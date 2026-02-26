from __future__ import annotations

from django.shortcuts import redirect, render
from django.urls import reverse

from symptom_checker.ai_client import AIGenerationError
from symptom_checker.engine import (
    get_or_build_result,
    has_active_session,
    question_context,
    reset_session,
    start_session,
    submit_answer,
)
from symptom_checker.schemas import IntakeData


def start(request):
    if request.method == "POST":
        return redirect("question")
    return render(request, "symptom_checker/start.html")


def question(request):
    if request.method == "POST" and "symptom" in request.POST:
        symptom = (request.POST.get("symptom") or "").strip()
        gender = (request.POST.get("gender") or "").strip()
        state = (request.POST.get("state") or "").strip()
        age_raw = (request.POST.get("age") or "").strip()
        if not symptom:
            return render(
                request,
                "symptom_checker/start.html",
                {"error_message": "Please enter your main symptom."},
            )

        try:
            age = int(age_raw) if age_raw else None
        except ValueError:
            return render(
                request,
                "symptom_checker/start.html",
                {"error_message": "Age must be a number."},
            )

        intake = IntakeData(age=age, gender=gender, state=state, symptom=symptom)
        try:
            start_session(request, intake)
        except AIGenerationError as exc:
            return render(
                request,
                "symptom_checker/start.html",
                {"error_message": f"Live AI question generation failed: {exc}"},
            )
        return redirect("question")

    if request.method == "POST" and "answer" in request.POST:
        if not has_active_session(request):
            return redirect("symptom_home")
        answer_value = (request.POST.get("answer") or "").strip()
        if answer_value:
            is_done = submit_answer(request, answer_value)
            if is_done:
                return redirect("result_page")

    context = question_context(request)
    if not context["has_session"]:
        return redirect("symptom_home")
    if context["completed"]:
        return redirect("result_page")

    return render(
        request,
        "symptom_checker/question.html",
        {
            "question": context["question"],
            "step": context["step"],
            "total": context["total"],
            "progress": context["progress"],
        },
    )


def result_page(request):
    if not has_active_session(request):
        return redirect("symptom_home")

    result = get_or_build_result(request)
    if not result:
        return redirect("symptom_home")

    diagnosis = result.get("diagnosis", {})
    conditions = diagnosis.get("conditions", [])
    return render(
        request,
        "symptom_checker/result.html",
        {
            "diagnosis": diagnosis,
            "conditions": conditions,
            "urgency": diagnosis.get("urgency", "Moderate"),
            "advice": diagnosis.get("advice", ""),
            "risk_banner": result.get("risk_banner", ""),
            "recommended_doctors": result.get("recommended_doctors", []),
            "recommended_articles": result.get("recommended_articles", []),
            "collectible": result.get("community_collectible", {}),
            "ai_calls": result.get("ai_calls", {}),
            "ai_error": result.get("ai_error", ""),
        },
    )


def reset_flow(request):
    reset_session(request)
    return redirect(reverse("symptom_home"))
