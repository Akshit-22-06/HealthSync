"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from authentication.views import*
from authentication import views
from dashboard import views as dashboard_views
from articles import views as articles_api
from community import views as community_views
from symptom_checker import views as symptom_checker_views
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('',guest_page, name="guest"),          # Guest page
    path('home/', views.home, name="home"),                 # Home page
    path("admin/", admin.site.urls),                  # Admin interface
    path('login/', views.login_page, name='login'),    # Login page
    path('register/', views.register_page, name='register'),# Registration page
    path('doctor/request-status/', views.doctor_request_status, name='doctor_request_status'),
    path('doctor/portal/', views.doctor_portal, name='doctor_portal'),
    path('dashboard/', dashboard_views.dashboard, name='dashboard'),
    path('articles-api/', articles_api.article, name='articles'),
    path('community/', community_views.community, name='community'),
    path('symptom-checker/', symptom_checker_views.symptom_checker, name='symptom_checker'),
    path('generate-blog/', articles_api.gemini_blog_generate, name='gemini_blog_generate'),
#     path('list-models/', articles_api.list_models, name='list_models'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
