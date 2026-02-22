# from openai import OpenAI
# from django.conf import settings

# client = OpenAI(api_key=settings.OPENAI_API_KEY)

# def generate_health_article(topic):

#     prompt = f"""
#     Write a blog-style health article about {topic}.
    
#     Make it:
#     - Easy to understand
#     - Around 600 words
#     - Structured with headings
#     - Practical tips included
#     - Professional but simple tone
    
#     Return in this format:
#     TITLE:
#     CONTENT:
#     """

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {"role": "system", "content": "You are a professional health writer."},
#             {"role": "user", "content": prompt}
#         ],
#         temperature=0.7
#     )

#     return response.choices[0].message.content
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
        except Exception as e:
            article = f"Error: {str(e)}"

    return render(request, "articles/gemini_blog.html", {
        "article": article,
        "topic": topic
    })