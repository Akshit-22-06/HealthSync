from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db.models import Q

from symptom_checker.gemini_engine import generate_adaptive_question
from symptom_checker.models import (
    BodyArea,
    Condition,
    ConditionScoreSnapshot,
    ConditionSymptom,
    DiagnosticQuestion,
    SessionAnswer,
    Symptom,
    SymptomSession,
)


CONFIDENCE_THRESHOLD = 0.70
MAX_QUESTIONS = 8
EMERGENCY_TERMS = (
    "chest pain",
    "difficulty breathing",
    "shortness of breath",
    "unconscious",
    "seizure",
    "heavy bleeding",
)


@dataclass
class EmergencyCheckResult:
    emergency: bool
    message: str = ""


def normalize_answer(answer_value: str, answer_type: str) -> bool | None:
    if answer_type != DiagnosticQuestion.ANSWER_YES_NO:
        return None
    if answer_value is None:
        return None
    normalized = answer_value.strip().lower()
    if normalized in {"yes", "true", "1"}:
        return True
    if normalized in {"no", "false", "0"}:
        return False
    return None


def emergency_precheck(initial_symptom: str) -> EmergencyCheckResult:
    text = (initial_symptom or "").strip().lower()
    for term in EMERGENCY_TERMS:
        if term in text:
            return EmergencyCheckResult(
                emergency=True,
                message="Your symptoms may require emergency care. Seek immediate help.",
            )
    return EmergencyCheckResult(emergency=False)


def _candidate_condition_ids(session: SymptomSession) -> set[int]:
    if not session.initial_symptom:
        return set(Condition.objects.values_list("id", flat=True))
    symptom_ids = set(
        Symptom.objects.filter(name__icontains=session.initial_symptom).values_list(
            "id", flat=True
        )
    )
    if not symptom_ids:
        return set(Condition.objects.values_list("id", flat=True))
    candidate_ids = set(
        ConditionSymptom.objects.filter(symptom_id__in=symptom_ids).values_list(
            "condition_id", flat=True
        )
    )
    if not candidate_ids:
        return set(Condition.objects.values_list("id", flat=True))
    return candidate_ids


def _confidence_map(scores: dict[int, float]) -> dict[int, float]:
    if not scores:
        return {}
    adjusted = {cid: max(score, 0.0) + 1.0 for cid, score in scores.items()}
    total = sum(adjusted.values())
    if total <= 0:
        return {cid: 0.0 for cid in scores}
    return {cid: adjusted[cid] / total for cid in scores}


def compute_condition_scores(session: SymptomSession) -> list[dict]:
    candidate_ids = _candidate_condition_ids(session)
    conditions = list(Condition.objects.filter(id__in=candidate_ids))
    scores = {condition.id: 0.0 for condition in conditions}
    red_flag_hit = False

    answers = (
        SessionAnswer.objects.filter(session=session)
        .select_related("question", "question__symptom")
        .order_by("answered_at")
    )

    for answer in answers:
        mappings = ConditionSymptom.objects.filter(
            condition_id__in=candidate_ids,
            symptom=answer.question.symptom,
        ).select_related("condition")
        for mapping in mappings:
            base = mapping.weight * answer.question.weight
            if answer.normalized_bool is True:
                scores[mapping.condition_id] += base
                if mapping.is_red_flag:
                    red_flag_hit = True
            elif answer.normalized_bool is False:
                scores[mapping.condition_id] -= base * 0.7

    confidence = _confidence_map(scores)
    ranked = sorted(
        (
            {
                "condition": condition,
                "score": scores.get(condition.id, 0.0),
                "confidence": confidence.get(condition.id, 0.0),
            }
            for condition in conditions
        ),
        key=lambda row: row["score"],
        reverse=True,
    )

    for row in ranked:
        ConditionScoreSnapshot.objects.update_or_create(
            session=session,
            condition=row["condition"],
            defaults={"score": row["score"], "confidence": row["confidence"]},
        )

    session.top_confidence = ranked[0]["confidence"] if ranked else 0.0
    if red_flag_hit and session.status != SymptomSession.STATUS_EMERGENCY:
        session.status = SymptomSession.STATUS_EMERGENCY
        session.emergency_message = (
            "A red-flag symptom was detected. Seek emergency care immediately."
        )
    session.save(update_fields=["top_confidence", "status", "emergency_message"])
    return ranked


def should_stop(session: SymptomSession, top_confidence: float) -> bool:
    if session.status == SymptomSession.STATUS_EMERGENCY:
        return True
    if session.current_step >= MAX_QUESTIONS:
        return True
    return top_confidence >= CONFIDENCE_THRESHOLD


def _active_condition_set(scored_rows: Iterable[dict]) -> set[int]:
    rows = list(scored_rows)
    if not rows:
        return set(Condition.objects.values_list("id", flat=True))
    keep = [row["condition"].id for row in rows[:5]]
    return set(keep)


def select_next_question(session: SymptomSession) -> DiagnosticQuestion | None:
    if session.current_step >= MAX_QUESTIONS:
        return None

    answered_question_ids = set(
        SessionAnswer.objects.filter(session=session).values_list("question_id", flat=True)
    )
    scored_rows = compute_condition_scores(session)
    active_conditions = _active_condition_set(scored_rows)
    total_active = max(len(active_conditions), 1)

    candidates = (
        DiagnosticQuestion.objects.filter(active=True)
        .exclude(id__in=answered_question_ids)
        .select_related("symptom")
    )

    best_question = None
    best_score = -1.0
    for question in candidates:
        linked_condition_ids = set(
            ConditionSymptom.objects.filter(symptom=question.symptom).values_list(
                "condition_id", flat=True
            )
        )
        if not linked_condition_ids:
            continue
        overlap = len(active_conditions.intersection(linked_condition_ids))
        ratio = overlap / total_active
        # Highest when symptom divides active conditions close to 50/50.
        split_quality = 1.0 - abs(ratio - 0.5) * 2
        information_proxy = max(split_quality, 0.0)
        question_score = (information_proxy * 2.0) + question.weight
        if question_score > best_score:
            best_question = question
            best_score = question_score
    if best_question is not None:
        return best_question
    return _fallback_question(session, answered_question_ids)


def _fallback_question(
    session: SymptomSession, answered_question_ids: set[int]
) -> DiagnosticQuestion | None:
    symptom_name = (session.initial_symptom or "").strip()
    if not symptom_name:
        return None

    # Reuse unanswered questions tied to this symptom before generating a new one.
    area, _ = BodyArea.objects.get_or_create(name="General")
    symptom = Symptom.objects.filter(name__iexact=symptom_name).first()
    if symptom is None:
        symptom = Symptom.objects.create(name=symptom_name, body_area=area)

    existing = (
        DiagnosticQuestion.objects.filter(symptom=symptom, active=True)
        .exclude(id__in=answered_question_ids)
        .order_by("-weight", "id")
        .first()
    )
    if existing:
        return existing

    answered_rows = (
        SessionAnswer.objects.filter(session=session)
        .select_related("question")
        .order_by("answered_at")
    )
    answered_pairs = [
        {"question": row.question.text, "answer": row.answer_value} for row in answered_rows
    ]
    generated, _ = generate_adaptive_question(
        initial_symptom=symptom_name,
        answered_pairs=answered_pairs,
        step=session.current_step + 1,
    )
    if not generated.get("text"):
        return None
    q_type = generated.get("answer_type", "yes_no")
    model_answer_type = (
        DiagnosticQuestion.ANSWER_SINGLE_CHOICE
        if q_type == "single_choice"
        else DiagnosticQuestion.ANSWER_YES_NO
    )
    q_text = (generated.get("text") or "").strip() or f"Are you still experiencing {symptom_name} right now?"
    options = generated.get("options") or []

    unique_text = q_text
    # Ensure we do not recreate an already answered fallback question.
    attempt = 1
    while True:
        candidate = DiagnosticQuestion.objects.filter(
            symptom=symptom, text=unique_text, active=True
        ).first()
        if candidate is None or candidate.id not in answered_question_ids:
            break
        attempt += 1
        unique_text = f"{q_text} ({attempt})"

    question, _ = DiagnosticQuestion.objects.get_or_create(
        text=unique_text,
        symptom=symptom,
        defaults={
            "answer_type": model_answer_type,
            "weight": 1.0,
            "active": True,
            "options": options,
        },
    )
    return question
