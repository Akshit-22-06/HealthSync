from __future__ import annotations

from symptom_checker.schemas import DiagnosisResult


def _risk_banner(urgency: str) -> str:
    label = (urgency or "").strip().lower()
    if label == "high":
        return "High-risk pattern detected. Seek urgent medical care now."
    if label == "moderate":
        return "Moderate-risk pattern detected. Arrange a doctor visit soon."
    return "Low-risk pattern detected. Continue monitoring and seek care if symptoms worsen."


def build_result_payload(*, diagnosis: DiagnosisResult) -> dict:
    return {
        "diagnosis": diagnosis.to_dict(),
        "risk_banner": _risk_banner(diagnosis.urgency),
    }
