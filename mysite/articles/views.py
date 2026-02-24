from unicodedata import category
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from html import escape
import logging
import re
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from .models import Article
from .forms import ArticleForm

logger = logging.getLogger(__name__)


def article(request):
    category = request.GET.get("category")
    search_query = request.GET.get("q")
    approved_articles = Article.objects.filter(status="approved")
    if category and category != "All":
        approved_articles = approved_articles.filter(category__iexact=category)
    if search_query:
            approved_articles = approved_articles.filter(
        Q(title__icontains=search_query) |
        Q(content__icontains=search_query)
)
    approved_articles = approved_articles.order_by("-created_at")
    is_doctor = False
    if request.user.is_authenticated:
        is_doctor = request.user.groups.filter(name="Doctor").exists()

    return render(request, 'articles/articles.html', {
        "approved_articles": approved_articles,
        "is_doctor": is_doctor,
        "selected_category": category or "All",
        "search_query": search_query or "",
        "categories": Article.objects.values_list("category", flat=True).distinct(),
    })


def is_doctor(user):
    if user.groups.filter(name="Doctor").exists():
        return True
    raise PermissionDenied


def is_admin(user):
    return user.groups.filter(name="Admin").exists()


try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None


def _inline_markdown_to_html(text: str) -> str:
    safe = escape(text)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"\*(.+?)\*", r"<em>\1</em>", safe)
    return safe


def _format_generated_article(raw_text: str) -> str:
    lines = (raw_text or "").splitlines()
    html_parts = []
    in_ul = False
    in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            html_parts.append("</ul>")
            in_ul = False
        if in_ol:
            html_parts.append("</ol>")
            in_ol = False

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            close_lists()
            continue

        if line.startswith("### "):
            close_lists()
            html_parts.append(f"<h3>{_inline_markdown_to_html(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            close_lists()
            html_parts.append(f"<h2>{_inline_markdown_to_html(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            close_lists()
            html_parts.append(f"<h1>{_inline_markdown_to_html(line[2:])}</h1>")
            continue

        if re.match(r"^(\*|-|•)\s+", line):
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            if not in_ul:
                html_parts.append("<ul>")
                in_ul = True
            item = re.sub(r"^(\*|-|•)\s+", "", line)
            html_parts.append(f"<li>{_inline_markdown_to_html(item)}</li>")
            continue

        if re.match(r"^\d+\.\s+", line):
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if not in_ol:
                html_parts.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s+", "", line)
            html_parts.append(f"<li>{_inline_markdown_to_html(item)}</li>")
            continue

        close_lists()
        html_parts.append(f"<p>{_inline_markdown_to_html(line)}</p>")

    close_lists()
    return "\n".join(html_parts)


def gemini_blog_generate(request):
    article_text = None
    article_html = None
    topic = None
    error_message = None

    if request.method == "POST":
        topic = (request.POST.get("topic") or "").strip()

        if not topic:
            error_message = "Please enter a health topic."
            return render(
                request,
                "articles/gemini_blog.html",
                {"article": article_text, "article_html": article_html, "topic": topic, "error_message": error_message},
            )

        prompt = f"""
        Write a professional blog-style health article about {topic}.
        Use clear headings and short paragraphs.
        Use simple bullet points where useful.
        Keep it around 600 words.
        Make it easy to understand.
        Include practical tips.
        Avoid markdown fences.
        """

        try:
            if genai is None:
                raise RuntimeError("Gemini SDK is not installed")

            if not settings.GEMINI_API_KEY:
                raise RuntimeError("GEMINI_API_KEY is not configured")

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            response = model.generate_content(prompt)
            article_text = response.text
            article_html = _format_generated_article(article_text)

        except Exception as e:
            logger.exception("Gemini blog generation failed: %s", e)
            error_message = "Could not generate article right now. Please try again."

    return render(request, "articles/gemini_blog.html", {
        "article": article_text,
        "article_html": article_html,
        "topic": topic,
        "error_message": error_message,
    })


@login_required
@user_passes_test(is_doctor)
def approve_article(request, id):
    article = get_object_or_404(Article, id=id)
    article.status = "approved"
    article.reviewer = request.user
    article.reviewed_at = timezone.now()
    article.save()
    return redirect("review_queue")


@login_required
@user_passes_test(is_doctor)
def reject_article(request, id):
    article = get_object_or_404(Article, id=id)
    article.status = "rejected"
    article.reviewer = request.user
    article.reviewed_at = timezone.now()
    article.rejection_reason = request.POST.get("rejection_reason", "")
    article.save()
    return redirect("review_queue")


@login_required
@user_passes_test(is_doctor)
def review_queue(request):
    pending_articles = Article.objects.filter(status="pending")
    return render(request, "articles/review_queue.html", {
        "pending_articles": pending_articles
    })


@login_required
def my_articles(request):
    user_articles = Article.objects.filter(
        author=request.user
    ).order_by("-created_at")

    return render(request, "articles/my_article.html", {
        "user_articles": user_articles
    })


@login_required
def post_article(request):
    if request.method == "POST":
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.status = "pending"
            article.save()
            return redirect("my_articles")
    else:
        form = ArticleForm()

    user_articles = Article.objects.filter(author=request.user)

    return render(request, "articles/my_article.html", {
        "form": form,
        "user_articles": user_articles
    })


@login_required
def delete_article(request, id):
    article = get_object_or_404(Article, id=id, author=request.user)

    if request.method == "POST":
        article.delete()
        return redirect("my_articles")

    return redirect("my_articles")
