from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class IntakeData:
    age: int | None
    gender: str
    state: str
    symptom: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntakeData":
        return cls(
            age=data.get("age"),
            gender=data.get("gender", ""),
            state=data.get("state", ""),
            symptom=data.get("symptom", ""),
        )


@dataclass
class QuestionItem:
    id: int
    text: str
    type: str = "yesno"
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestionItem":
        return cls(
            id=int(data.get("id", 0)),
            text=data.get("text", ""),
            type=data.get("type", "yesno"),
            options=list(data.get("options", [])),
        )


@dataclass
class AnswerItem:
    question_id: int
    question_text: str
    answer: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnswerItem":
        return cls(
            question_id=int(data.get("question_id", 0)),
            question_text=data.get("question_text", ""),
            answer=data.get("answer", ""),
        )


@dataclass
class DiagnosisCondition:
    name: str
    likelihood: str = ""
    reasoning: str = ""
    specialization: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagnosisCondition":
        return cls(
            name=data.get("name", ""),
            likelihood=data.get("likelihood", ""),
            reasoning=data.get("reasoning", ""),
            specialization=data.get("specialization", ""),
        )


@dataclass
class DiagnosisResult:
    conditions: list[DiagnosisCondition]
    urgency: str
    advice: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "conditions": [condition.to_dict() for condition in self.conditions],
            "urgency": self.urgency,
            "advice": self.advice,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DiagnosisResult":
        rows = data.get("conditions", []) or []
        return cls(
            conditions=[DiagnosisCondition.from_dict(row) for row in rows],
            urgency=data.get("urgency", "Moderate"),
            advice=data.get("advice", "Consult a qualified doctor for evaluation."),
        )
