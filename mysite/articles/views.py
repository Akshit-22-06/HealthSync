from django.shortcuts import render
from django.conf import settings
from html import escape
import logging
import re

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None

logger = logging.getLogger(__name__)


def article(request):
    return render(request, 'articles/articles.html')


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

    def close_lists() -> None:
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

    article = None
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
                {"article": article, "article_html": article_html, "topic": topic, "error_message": error_message},
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
            article = response.text
            article_html = _format_generated_article(article)
        except Exception as e:
            logger.exception("Gemini blog generation failed: %s", e)
            lower_err = str(e).lower()

            if "api key not valid" in lower_err or "api_key_invalid" in lower_err:
                error_message = "Gemini API key is invalid. Update GEMINI_API_KEY in your .env file and restart the server."
            elif "not configured" in lower_err:
                error_message = "GEMINI_API_KEY is missing. Add it to your .env file and restart the server."
            elif "not installed" in lower_err:
                error_message = "Gemini SDK is not installed. Install dependencies and try again."
            else:
                error_message = "Could not generate article right now. Please try again."

    return render(request, "articles/gemini_blog.html", {
        "article": article,
        "article_html": article_html,
        "topic": topic,
        "error_message": error_message,
    })
