from __future__ import annotations

import json
import os
import re
import time

from symptom_checker.schemas import (
    AnswerItem,
    DiagnosisCondition,
    DiagnosisResult,
    IntakeData,
    QuestionItem,
)

try:
    from google import genai
except Exception:
    genai = None


class AIGenerationError(RuntimeError):
    pass


def _client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def _parse_json(text: str):
    cleaned = (text or "").replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def _generate_content_with_retry(prompt: str, *, retries: int = 2):
    client = _client()
    if client is None:
        raise AIGenerationError("Gemini client unavailable. Check GEMINI_API_KEY and SDK setup.")
    last_error = None
    for attempt in range(retries + 1):
        try:
            return client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
    raise AIGenerationError(_friendly_error(last_error))


def _friendly_error(exc: Exception | None) -> str:
    message = str(exc or "")
    lowered = message.lower()
    if "resource_exhausted" in lowered or "quota" in lowered or "429" in lowered:
        retry_match = re.search(r"retryDelay['\"]?\s*:\s*['\"]?(\d+)s", message)
        retry_hint = f" Retry in about {retry_match.group(1)} seconds." if retry_match else ""
        return (
            "Gemini quota exceeded for this project/model (429 RESOURCE_EXHAUSTED). "
            "A new API key in the same project will not bypass quota." + retry_hint
        )
    if "api key not valid" in lowered or "invalid api key" in lowered or "401" in lowered:
        return "Gemini API key is invalid or unauthorized (401). Update GEMINI_API_KEY and restart server."
    if "permission" in lowered or "403" in lowered:
        return "Gemini request forbidden (403). Check project permissions, API enablement, and billing."
    return "Gemini request failed. Check API key, billing, and model access."


def _validate_question(row: dict, idx: int) -> QuestionItem:
    item = QuestionItem.from_dict(row)
    item.id = idx
    item.text = item.text.strip()
    item.type = (item.type or "yesno").strip().lower()
    if not item.text:
        raise AIGenerationError("AI returned an empty question.")
    if item.type not in {"yesno", "text", "single_choice"}:
        raise AIGenerationError(f"AI returned unsupported question type: {item.type}")
    if item.type == "single_choice":
        item.options = [str(opt).strip() for opt in (item.options or []) if str(opt).strip()]
        if len(item.options) < 2 or len(item.options) > 4:
            raise AIGenerationError("AI single_choice question must include 2-4 options.")
    else:
        item.options = []
    return item


def generate_questions(intake: IntakeData) -> list[QuestionItem]:
    prompt = f"""
You are a medical intake assistant.
Generate 6-8 follow-up triage questions for this user.
Return ONLY valid JSON array, no markdown.

Each item schema:
{{
  "id": 1,
  "text": "question text",
  "type": "yesno | text | single_choice",
  "options": ["option 1", "option 2"]
}}

Rules:
- Keep questions concise and practical.
- Ask one thing per question.
- Use yesno for most questions.
- If single_choice, provide 2-4 options.
- Do not repeat questions.
- This must be AI-generated output. Include "ai_generated": true in every item.

User profile:
Age: {intake.age}
Gender: {intake.gender}
State: {intake.state}
Primary symptom: {intake.symptom}
"""

    response = _generate_content_with_retry(prompt)
    try:
        parsed = _parse_json(response.text)
    except Exception as exc:
        raise AIGenerationError(f"Could not parse AI questions JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise AIGenerationError("AI questions response must be a JSON array.")
    if len(parsed) < 6 or len(parsed) > 8:
        raise AIGenerationError("AI must return 6-8 questions.")

    questions: list[QuestionItem] = []
    seen: set[str] = set()
    for idx, row in enumerate(parsed, start=1):
        if not isinstance(row, dict):
            raise AIGenerationError("AI question items must be JSON objects.")
        if row.get("ai_generated") is not True:
            raise AIGenerationError("AI generation marker missing for question item.")
        question = _validate_question(row, idx)
        signature = question.text.lower()
        if signature in seen:
            raise AIGenerationError("AI returned duplicate questions.")
        seen.add(signature)
        questions.append(question)
    return questions


def generate_diagnosis(intake: IntakeData, answers: list[AnswerItem]) -> DiagnosisResult:
    answer_lines = "\n".join(
        f"- Q: {answer.question_text} | A: {answer.answer}" for answer in answers
    )
    prompt = f"""
You are a clinical triage assistant.
Analyze user intake and follow-up responses.
Return ONLY valid JSON object, no markdown.

Schema:
{{
  "conditions": [
    {{
      "name": "Condition",
      "likelihood": "High | Medium | Low",
      "reasoning": "short explanation",
      "specialization": "doctor specialization"
    }}
  ],
  "urgency": "Low | Moderate | High",
  "advice": "short actionable guidance",
  "ai_generated": true
}}

User profile:
Age: {intake.age}
Gender: {intake.gender}
State: {intake.state}
Primary symptom: {intake.symptom}

Follow-up answers:
{answer_lines}
"""

    response = _generate_content_with_retry(prompt)
    try:
        parsed = _parse_json(response.text)
    except Exception as exc:
        raise AIGenerationError(f"Could not parse AI diagnosis JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise AIGenerationError("AI diagnosis response must be a JSON object.")
    if parsed.get("ai_generated") is not True:
        raise AIGenerationError("AI generation marker missing for diagnosis.")
    diagnosis = DiagnosisResult.from_dict(parsed)
    diagnosis.conditions = [c for c in diagnosis.conditions if c.name.strip()]
    if not diagnosis.conditions:
        raise AIGenerationError("AI diagnosis returned no valid conditions.")
    if diagnosis.urgency not in {"Low", "Moderate", "High"}:
        raise AIGenerationError("AI diagnosis returned invalid urgency.")
    if not diagnosis.advice.strip():
        raise AIGenerationError("AI diagnosis returned empty advice.")
    return diagnosis
