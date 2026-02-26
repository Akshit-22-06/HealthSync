from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .forms import ProfileUpdateForm
from django.contrib.auth import get_user_model
from articles.models import Article  # adjust if model name different
from dashboard.models import HealthLog  # adjust if different

@login_required(login_url="/login/")
def profile_view(request):

    user = request.user

    # Health Logs
    logs = HealthLog.objects.filter(user=user)
    total_logs = logs.count()

    if total_logs > 0:
        avg_score = round(sum(log.health_score for log in logs) / total_logs, 2)
    else:
        avg_score = None

    # Articles
    articles = Article.objects.filter(author=user)
    article_count = articles.count()

    context = {
        "total_logs": total_logs,
        "avg_score": avg_score,
        "articles": articles,
        "article_count": article_count,
    }

    return render(request, "accounts/profile.html", context)


@login_required(login_url="/login/")
def edit_profile(request):
    if request.method == "POST":
        form = ProfileUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, "accounts/edit_profile.html", {"form": form})


@login_required(login_url="/login/")
def logout_view(request):
    logout(request)
    return redirect("login")