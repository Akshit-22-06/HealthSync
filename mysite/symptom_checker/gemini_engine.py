import os
import json
import time

try:
    from google import genai
except Exception:
    genai = None


_DISABLE_UNTIL = 0.0


def _client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def _can_call_gemini() -> bool:
    return time.time() >= _DISABLE_UNTIL


def _disable_temporarily(seconds: int = 30):
    global _DISABLE_UNTIL
    _DISABLE_UNTIL = time.time() + seconds


def rephrase_question(question_text: str, symptom_name: str) -> tuple[str, bool]:
    if not _can_call_gemini():
        return question_text, False
    client = _client()
    if client is None:
        return question_text, False

    prompt = f"""
Rewrite this medical screening question in concise, empathetic language.
Return plain text only.

Main symptom: {symptom_name}
Question: {question_text}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = (response.text or "").strip()
        if not text:
            return question_text, False
        return text, True
    except Exception:
        _disable_temporarily()
        return question_text, False


def empathy_line(symptom: str) -> tuple[str, bool]:
    if not _can_call_gemini():
        return "", False
    client = _client()
    if client is None:
        return "", False

    prompt = f"""
Write one short and calm line to reassure a user starting a symptom check.
Main symptom: {symptom}
Return plain text only, <= 20 words.
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = (response.text or "").strip()
        return text, bool(text)
    except Exception:
        _disable_temporarily()
        return "", False


def generate_adaptive_question(
    *, initial_symptom: str, answered_pairs: list[dict], step: int
) -> tuple[dict, bool]:
    empty = {"text": "", "answer_type": "yes_no", "options": []}

    if not _can_call_gemini():
        return empty, False
    client = _client()
    if client is None:
        return empty, False

    prompt = f"""
You are a medical triage assistant.
Generate the NEXT single screening question based on history.
Return strict JSON only with keys: text, answer_type, options, ai_generated.
answer_type must be "yes_no" or "single_choice".
If "yes_no", options must be [].
If "single_choice", options must contain 2-5 short choices.
Set ai_generated to true.

Initial symptom: {initial_symptom}
Step: {step}
Answered history: {answered_pairs}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = (response.text or "").replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        q_text = (parsed.get("text") or "").strip()
        q_type = (parsed.get("answer_type") or "").strip().lower()
        q_options = parsed.get("options") or []
        if parsed.get("ai_generated") is not True:
            return empty, False
        if not q_text or q_type not in {"yes_no", "single_choice"}:
            return empty, False
        if q_type == "yes_no":
            q_options = []
        else:
            q_options = [str(opt).strip() for opt in q_options if str(opt).strip()]
            if len(q_options) < 2 or len(q_options) > 5:
                return empty, False
        return {"text": q_text, "answer_type": q_type, "options": q_options}, True
    except Exception:
        _disable_temporarily()
        return empty, False
