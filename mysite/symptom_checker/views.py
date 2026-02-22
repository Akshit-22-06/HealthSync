from django.shortcuts import render, redirect
from django.http import HttpResponse
from .engine import run_engine, get_question_by_index


# ===============================
# START PAGE
# ===============================
def symptom_home(request):
    # Reset session answers
    request.session["answers"] = {}
    return redirect("symptom_question", q_index=0)


# ===============================
# QUESTION FLOW PAGE
# ===============================
def symptom_question(request, q_index):
    q_index = int(q_index)
    question = get_question_by_index(q_index)

    if question is None:
        return redirect("symptom_result")

    if request.method == "POST":
        answers = request.session.get("answers", {})

        value = request.POST.get("answer")

        # Save answer in session
        answers[question["id"]] = value
        request.session["answers"] = answers

        return redirect("symptom_question", q_index=q_index + 1)

    context = {
        "question": question,
        "q_index": q_index,
    }

    return render(request, "symptom_checker/question.html", context)


# ===============================
# RESULT PAGE
# ===============================
def symptom_result(request):
    answers = request.session.get("answers", {})
    results = run_engine(answers)

    context = {
        "results": results
    }

    return render(request, "symptom_checker/result.html", context)
