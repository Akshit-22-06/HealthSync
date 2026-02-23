from collections import defaultdict
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import HealthLog
from .forms import HealthLogForm


# ==================================
# SCORE CALCULATION (OUT OF 10)
# ==================================
def calculate_score(log):
    sleep_score = min(float(log.sleep_hours) / 8, 1) * 2.5
    water_score = min(float(log.water_liters) / 3, 1) * 2.5
    mood_score = (log.mood / 5) * 2.5
    exercise_score = min(log.exercise_minutes / 60, 1) * 2.5

    return round(sleep_score + water_score + mood_score + exercise_score, 2)


# ==================================
# DASHBOARD
# ==================================
@login_required
def dashboard(request):

    # ---- Handle Form Submission ----
    if request.method == "POST":
        form = HealthLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            log.save()
            return redirect("dashboard")
    else:
        form = HealthLogForm()

    # ---- Fetch Logs (Newest First) ----
    logs = list(
        HealthLog.objects.filter(user=request.user).order_by("-date")
    )

    # ---- Calculate Score Per Log ----
    for log in logs:
        log.total_score = calculate_score(log)

    # ---- Calculate Averages ----
    if logs:
        avg_sleep = sum(float(l.sleep_hours) for l in logs) / len(logs)
        avg_water = sum(float(l.water_liters) for l in logs) / len(logs)
        avg_mood = sum(l.mood for l in logs) / len(logs)
        avg_exercise = sum(l.exercise_minutes for l in logs) / len(logs)
        avg_score = sum(l.total_score for l in logs) / len(logs)
    else:
        avg_sleep = avg_water = avg_mood = avg_exercise = avg_score = 0

    # ---- Personalized Tips ----
    tips = []

    if avg_sleep < 6:
        tips.append("You are sleeping less than recommended 7-8 hours.")
    if avg_water < 2:
        tips.append("Increase your daily water intake.")
    if avg_exercise < 30:
        tips.append("Try at least 30 minutes of exercise daily.")
    if avg_mood < 3:
        tips.append("Your mood seems low. Consider relaxation or meditation.")

    if not tips:
        tips.append("Great job! Keep maintaining your healthy routine.")

    # ==================================
    # DAILY CHART DATA
    # ==================================
    daily_labels = [log.date.strftime("%b %d") for log in reversed(logs)]
    sleep_data = [float(log.sleep_hours) for log in reversed(logs)]
    mood_data = [log.mood for log in reversed(logs)]
    exercise_data = [log.exercise_minutes for log in reversed(logs)]
    score_data = [log.total_score for log in reversed(logs)]

    # ==================================
    # MONTHLY GROUPING (MAIN CHART)
    # ==================================
    monthly_scores = defaultdict(list)

    for log in logs:
        month_key = log.date.strftime("%b %Y")
        monthly_scores[month_key].append(log.total_score)

    monthly_labels = []
    monthly_avg_scores = []

    for month, scores in sorted(
        monthly_scores.items(),
        key=lambda x: datetime.strptime(x[0], "%b %Y")
    ):
        monthly_labels.append(month)
        monthly_avg_scores.append(round(sum(scores) / len(scores), 2))

    context = {
        "form": form,
        "logs": logs,
        "avg_sleep": round(avg_sleep, 1),
        "avg_water": round(avg_water, 1),
        "avg_mood": round(avg_mood, 1),
        "avg_exercise": round(avg_exercise, 1),
        "avg_score": round(avg_score, 2),
        "tips": tips,
        "daily_labels": daily_labels,
        "sleep_data": sleep_data,
        "mood_data": mood_data,
        "exercise_data": exercise_data,
        "score_data": score_data,
        "monthly_labels": monthly_labels,
        "monthly_scores": monthly_avg_scores,
        "has_logs": bool(logs),
    }

    return render(request, "dashboard/dashboard.html", context)


# ==================================
# EDIT LOG
# ==================================
@login_required
def edit_log(request, pk):
    log = get_object_or_404(HealthLog, pk=pk, user=request.user)

    if request.method == "POST":
        form = HealthLogForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            return redirect("dashboard")
    else:
        form = HealthLogForm(instance=log)

    return render(request, "dashboard/edit_log.html", {"form": form})


# ==================================
# DELETE LOG
# ==================================
@login_required
def delete_log(request, pk):
    log = get_object_or_404(HealthLog, pk=pk, user=request.user)
    log.delete()
    return redirect("dashboard")