from __future__ import annotations

import re
from urllib.parse import quote_plus

from symptom_checker.ai_client import AIGenerationError, generate_diagnosis, generate_questions
from symptom_checker.diagnosis import build_result_payload
from symptom_checker.models import Doctor
from symptom_checker.question_flow import append_answer, current_question, next_index
from symptom_checker.schemas import AnswerItem, DiagnosisResult, IntakeData, QuestionItem
from symptom_checker.services.doctor_discovery import discover_nearby_doctors
from symptom_checker.services.recommendations import (
    issue_collectible_tag,
    recommended_articles,
)


SESSION_KEY = "symptom_checker_flow"

SPECIALIZATION_KEYWORDS = {
    "dermatologist": {"skin", "fungal", "eczema", "psoriasis", "rash", "acne", "dermatitis"},
    "infectious disease specialist": {
        "infection",
        "infectious",
        "viral",
        "bacterial",
        "hiv",
        "aids",
        "fever",
        "tuberculosis",
        "tb",
    },
    "ent specialist": {"ear", "nose", "throat", "sinus", "tonsil", "hearing", "vertigo"},
    "pulmonologist": {"lung", "respiratory", "asthma", "cough", "breath", "pneumonia", "copd"},
    "cardiologist": {"heart", "cardiac", "chest pain", "hypertension", "bp", "arrhythmia"},
    "neurologist": {"neuro", "brain", "seizure", "migraine", "stroke", "nerve"},
    "gastroenterologist": {
        "stomach",
        "gastric",
        "liver",
        "abdomen",
        "gut",
        "hepatitis",
        "diarrhea",
    },
    "gynecologist": {"pregnancy", "uterus", "ovary", "menstrual", "pcos", "vaginal"},
    "orthopedic specialist": {"bone", "joint", "fracture", "sprain", "arthritis", "muscle", "spine"},
    "urologist": {"urine", "kidney", "bladder", "prostate", "urology"},
    "psychiatrist": {"anxiety", "depression", "mental", "panic", "mood", "psychiatric"},
    "endocrinologist": {"thyroid", "diabetes", "hormone", "endocrine"},
    "general physician": set(),
}


def _initial_state() -> dict:
    return {
        "intake": {},
        "questions": [],
        "answers": [],
        "current_index": 0,
        "diagnosis": None,
        "diagnosis_error": "",
        "ai_calls": {"questions": 0, "diagnosis": 0},
    }


def _flow(request) -> dict:
    return request.session.get(SESSION_KEY, _initial_state())


def _save_flow(request, flow: dict) -> None:
    request.session[SESSION_KEY] = flow
    request.session.modified = True


def start_session(request, intake: IntakeData) -> None:
    ai_questions = generate_questions(intake)
    questions = [question.to_dict() for question in ai_questions]
    flow = _initial_state()
    flow["intake"] = intake.to_dict()
    flow["questions"] = questions
    flow["answers"] = []
    flow["current_index"] = 0
    flow["diagnosis"] = None
    flow["diagnosis_error"] = ""
    flow["ai_calls"] = {"questions": 1, "diagnosis": 0}
    _save_flow(request, flow)


def has_active_session(request) -> bool:
    flow = _flow(request)
    return bool(flow.get("questions")) and bool(flow.get("intake"))


def question_context(request) -> dict:
    flow = _flow(request)
    questions = [QuestionItem.from_dict(row) for row in flow.get("questions", [])]
    idx = int(flow.get("current_index", 0))
    question = current_question(questions, idx)
    total = len(questions)
    return {
        "has_session": has_active_session(request),
        "completed": question is None,
        "question": question,
        "step": idx + 1,
        "total": total,
        "progress": int(((idx + 1) / total) * 100) if total else 0,
    }


def submit_answer(request, answer_value: str) -> bool:
    flow = _flow(request)
    questions = [QuestionItem.from_dict(row) for row in flow.get("questions", [])]
    answers = [AnswerItem.from_dict(row) for row in flow.get("answers", [])]
    idx = int(flow.get("current_index", 0))
    question = current_question(questions, idx)
    if question is None:
        return True

    updated_answers = append_answer(answers, question, answer_value)
    flow["answers"] = [answer.to_dict() for answer in updated_answers]
    flow["current_index"] = next_index(idx)
    _save_flow(request, flow)
    return flow["current_index"] >= len(questions)


def _top_conditions_from_diagnosis(condition_names: list[str]) -> list[str]:
    return [name.strip() for name in condition_names if name and name.strip()][:3]


def _tokenize(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-zA-Z0-9]+", (text or "").lower()) if t}


def _recommended_specializations(condition_rows: list[dict]) -> list[str]:
    recommended: list[str] = []
    seen: set[str] = set()

    # 1) Use model-provided specialization first (can be comma-separated).
    for row in condition_rows:
        if not isinstance(row, dict):
            continue
        raw = (row.get("specialization") or "").strip()
        if not raw:
            continue
        for part in [p.strip() for p in raw.split(",") if p.strip()]:
            key = part.lower()
            if key in seen:
                continue
            seen.add(key)
            recommended.append(part)

    # 2) Infer category specialists from condition names/reasoning.
    combined_text = " ".join(
        f"{row.get('name', '')} {row.get('reasoning', '')}"
        for row in condition_rows
        if isinstance(row, dict)
    )
    tokens = _tokenize(combined_text)
    for specialist, keywords in SPECIALIZATION_KEYWORDS.items():
        if keywords and tokens.intersection(keywords):
            if specialist not in seen:
                seen.add(specialist)
                recommended.append(specialist.title())

    if not recommended:
        recommended.append("General Physician")
    return recommended[:4]


def _doctors_for_specializations(specializations: list[str]) -> list[dict]:
    normalized_specs = [s.strip().lower() for s in specializations if s and s.strip()]
    if not normalized_specs:
        return []

    doctors = Doctor.objects.all()
    result = []
    for doctor in doctors:
        doc_spec = (doctor.specialization or "").lower()
        if any(spec in doc_spec for spec in normalized_specs):
            city = doctor.city or ""
            query = quote_plus(f"{doctor.name} {doctor.specialization} {city}".strip())
            map_search_url = f"https://www.google.com/maps/search/?api=1&query={query}"
            result.append(
                {
                    "name": doctor.name,
                    "specialization": doctor.specialization,
                    "city": city,
                    "phone": doctor.phone,
                    "email": doctor.email,
                    "latitude": doctor.latitude,
                    "longitude": doctor.longitude,
                    "map_search_url": map_search_url,
                    "source": "HealthSync DB",
                }
            )
    return result[:6]


def _external_doctor_matches(specializations: list[str], intake: IntakeData) -> list[dict]:
    scoped_specializations = [s for s in specializations if s and s.strip()] or ["General Physician"]
    location = intake.state or "India"
    found: list[dict] = []
    seen_names: set[str] = set()
    for specialization in scoped_specializations[:3]:
        rows = discover_nearby_doctors(
            location=location,
            specialization=specialization,
            limit=4,
        )
        for row in rows:
            name_key = (row.get("name") or "").strip().lower()
            if not name_key or name_key in seen_names:
                continue
            seen_names.add(name_key)
            found.append(row)
            if len(found) >= 6:
                return found
    return found


def get_or_build_result(request) -> dict:
    flow = _flow(request)
    if not has_active_session(request):
        return {}

    if flow.get("diagnosis"):
        diagnosis_payload = flow["diagnosis"]
        diagnosis_error = flow.get("diagnosis_error", "")
    else:
        intake = IntakeData.from_dict(flow["intake"])
        answers = [AnswerItem.from_dict(row) for row in flow.get("answers", [])]
        try:
            diagnosis = generate_diagnosis(intake, answers)
            diagnosis_payload = diagnosis.to_dict()
            diagnosis_error = ""
            flow["diagnosis"] = diagnosis_payload
            flow["ai_calls"]["diagnosis"] = 1
        except AIGenerationError as exc:
            diagnosis_payload = DiagnosisResult(
                conditions=[],
                urgency="Moderate",
                advice="Assessment unavailable because live AI generation failed. Please retry shortly.",
            ).to_dict()
            diagnosis_error = str(exc)
            flow["diagnosis"] = diagnosis_payload
            flow["diagnosis_error"] = diagnosis_error
        _save_flow(request, flow)

    built = build_result_payload(
        diagnosis=DiagnosisResult.from_dict(diagnosis_payload)
    )

    condition_rows = diagnosis_payload.get("conditions", []) or []
    target_specializations = _recommended_specializations(condition_rows)
    top_condition_names = _top_conditions_from_diagnosis(
        [row.get("name", "") for row in condition_rows if isinstance(row, dict)]
    )
    intake = IntakeData.from_dict(flow.get("intake", {}))
    db_docs = _doctors_for_specializations(target_specializations)
    external_docs = _external_doctor_matches(target_specializations, intake)
    recommended_docs = db_docs[:]
    known_names = {(d.get("name") or "").strip().lower() for d in recommended_docs}
    for doc in external_docs:
        key = (doc.get("name") or "").strip().lower()
        if key and key not in known_names:
            known_names.add(key)
            recommended_docs.append(doc)
        if len(recommended_docs) >= 6:
            break
    recommended_reads = recommended_articles(top_condition_names)
    collectible = issue_collectible_tag()

    built["recommended_doctors"] = recommended_docs
    built["recommended_specializations"] = target_specializations
    built["recommended_articles"] = recommended_reads
    built["ai_calls"] = flow.get("ai_calls", {"questions": 1, "diagnosis": 1})
    built["ai_error"] = diagnosis_error
    if collectible and getattr(collectible, "tag_code", ""):
        built["community_collectible"] = {
            "tag_code": collectible.tag_code,
            "label": collectible.display_label,
            "community_url": f"/community/?tag={collectible.tag_code}",
        }
    else:
        built["community_collectible"] = {}
    return built


def reset_session(request) -> None:
    if SESSION_KEY in request.session:
        del request.session[SESSION_KEY]
        request.session.modified = True
