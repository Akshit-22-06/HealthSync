from __future__ import annotations

from django.utils import timezone

from symptom_checker.ai_client import AIGenerationError, generate_diagnosis, generate_questions
from symptom_checker.diagnosis import build_result_payload
from symptom_checker.models import Condition, SymptomSession
from symptom_checker.question_flow import append_answer, current_question, next_index
from symptom_checker.schemas import AnswerItem, DiagnosisResult, IntakeData, QuestionItem
from symptom_checker.services.recommendations import (
    issue_collectible_tag,
    recommended_articles,
)
from symptom_checker.services.triage import match_doctors_for_specializations


SESSION_KEY = "symptom_checker_flow"


def _initial_state() -> dict:
    return {
        "session_id": None,
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

    db_session = SymptomSession.objects.create(
        user=request.user if getattr(request.user, "is_authenticated", False) else None,
        initial_symptom=intake.symptom,
        age=intake.age,
        gender=intake.gender,
        state=intake.state,
        status=SymptomSession.STATUS_ACTIVE,
    )
    flow = _initial_state()
    flow["session_id"] = str(db_session.id)
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


def _top_conditions_from_diagnosis(condition_names: list[str]) -> list[Condition]:
    matched: list[Condition] = []
    for name in condition_names:
        candidate = Condition.objects.filter(name__icontains=name).first()
        if candidate:
            matched.append(candidate)
    return matched[:3]


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

    condition_names = [row.get("name", "") for row in diagnosis_payload.get("conditions", [])]
    matched_conditions = _top_conditions_from_diagnosis(condition_names)
    recommended_docs = match_doctors_for_specializations(
        [c.specialization for c in matched_conditions if c.specialization]
    )
    recommended_reads = recommended_articles(matched_conditions)

    session_id = flow.get("session_id")
    collectible = None
    if session_id:
        db_session = SymptomSession.objects.filter(id=session_id).first()
        if db_session:
            if db_session.status != SymptomSession.STATUS_COMPLETED:
                db_session.status = SymptomSession.STATUS_COMPLETED
                db_session.completed_at = timezone.now()
                db_session.save(update_fields=["status", "completed_at"])
            collectible = issue_collectible_tag(
                db_session,
                matched_conditions[0] if matched_conditions else None,
            )

    built["recommended_doctors"] = recommended_docs
    built["recommended_articles"] = recommended_reads
    built["ai_calls"] = flow.get("ai_calls", {"questions": 1, "diagnosis": 1})
    built["ai_error"] = diagnosis_error
    if collectible:
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
