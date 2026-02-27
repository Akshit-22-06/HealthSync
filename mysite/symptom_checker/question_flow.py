from __future__ import annotations

from symptom_checker.schemas import AnswerItem, QuestionItem


def current_question(questions: list[QuestionItem], current_index: int) -> QuestionItem | None:
    if current_index < 0 or current_index >= len(questions):
        return None
    return questions[current_index]


def append_answer(
    answers: list[AnswerItem], question: QuestionItem, answer_value: str
) -> list[AnswerItem]:
    updated = list(answers)
    updated.append(
        AnswerItem(
            question_id=question.id,
            question_text=question.text,
            answer=answer_value,
        )
    )
    return updated


def next_index(current_index: int) -> int:
    return current_index + 1
