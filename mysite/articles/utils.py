import google.generativeai as genai
from django.shortcuts import render
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def gemini_blog_generator(request):

    article = None
    topic = None

    if request.method == "POST":
        topic = request.POST.get("topic")

        prompt = f"""
        Write a professional blog-style health article about {topic}.
        Use headings.
        Keep it around 600 words.
        Make it easy to understand.
        Include practical tips.
        """

        try:
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            response = model.generate_content(prompt)
            article = response.text
        except Exception as exc:
            article = f"Error: {exc}"

    return render(request, "articles/gemini_blog.html", {
        "article": article,
        "topic": topic
    })
