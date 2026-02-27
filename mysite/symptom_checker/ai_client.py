from __future__ import annotations

import json
import os
import re
import time
from urllib import error as urlerror
from urllib import request as urlrequest

from django.conf import settings

from symptom_checker.schemas import (
    AnswerItem,
    DiagnosisCondition,
    DiagnosisResult,
    IntakeData,
    QuestionItem,
)

class AIGenerationError(RuntimeError):
    pass


def _read_config(name: str, default: str = "") -> str:
    candidates = [os.getenv(name), getattr(settings, name, None), default]
    for raw in candidates:
        value = str(raw or "").strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1].strip()
        if value:
            return value
    return ""


def _parse_json(text: str):
    cleaned = (text or "").replace("```json", "").replace("```", "").strip()
    return json.loads(cleaned)


def _generate_content_with_retry(prompt: str, *, retries: int = 2):
    api_key = _read_config("GEMINI_API_KEY")
    model = _read_config("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        raise AIGenerationError(
            "Gemini API key missing. Set GEMINI_API_KEY in .env and restart server."
        )

    last_error = None
    for attempt in range(retries + 1):
        try:
            return _call_gemini(prompt=prompt, api_key=api_key, model=model)
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
    raise AIGenerationError(_friendly_error(last_error))


def _call_gemini(*, prompt: str, api_key: str, model: str) -> str:
    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "You are a strict JSON generator. Return only valid JSON.\n\n"
                            + prompt
                        )
                    }
                ],
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }
    req = urlrequest.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {raw}") from exc
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc

    candidates = payload.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")
    parts = ((candidates[0].get("content") or {}).get("parts") or [])
    content = ""
    for part in parts:
        text = (part.get("text") or "").strip()
        if text:
            content += text
    if not content:
        raise RuntimeError("Gemini returned empty content.")
    return content


def _friendly_error(exc: Exception | None) -> str:
    message = str(exc or "")
    lowered = message.lower()
    if "not found for api version" in lowered or "is not found" in lowered or "404" in lowered:
        return (
            "Gemini model name is invalid/unsupported for this endpoint. "
            "Use GEMINI_MODEL=gemini-2.5-flash."
        )
    if "reported as leaked" in lowered or "api key was reported as leaked" in lowered:
        return "Gemini rejected this key because it was reported as leaked. Generate a new Gemini API key and replace GEMINI_API_KEY."
    if "quota" in lowered or "429" in lowered or "rate limit" in lowered:
        retry_match = re.search(r"retry[^0-9]*(\d+)", message)
        retry_hint = f" Retry in about {retry_match.group(1)} seconds." if retry_match else ""
        return "Gemini rate/quota limit reached (429). Retry shortly." + retry_hint
    if "invalid api key" in lowered or "incorrect api key" in lowered or "401" in lowered:
        return "Gemini API key is invalid or unauthorized (401). Update GEMINI_API_KEY and restart server."
    if "permission" in lowered or "forbidden" in lowered or "403" in lowered:
        return "Gemini request forbidden (403). Check key permissions, API enablement, and model access."
    return "Gemini request failed. Check GEMINI_API_KEY, model name, and quota."


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
Generate exactly 15 follow-up triage questions for this user.
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
- Ensure all 15 questions are clinically meaningful and non-redundant.
- This must be AI-generated output. Include "ai_generated": true in every item.

User profile:
Age: {intake.age}
Gender: {intake.gender}
State: {intake.state}
Primary symptom: {intake.symptom}
"""

    response = _generate_content_with_retry(prompt)
    try:
        parsed = _parse_json(response)
    except Exception as exc:
        raise AIGenerationError(f"Could not parse AI questions JSON: {exc}") from exc

    if not isinstance(parsed, list):
        raise AIGenerationError("AI questions response must be a JSON array.")
    if len(parsed) != 15:
        raise AIGenerationError("AI must return exactly 15 questions.")

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
        parsed = _parse_json(response)
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
