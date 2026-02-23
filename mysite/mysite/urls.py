from django.contrib import admin
from django.urls import path, include
from authentication.views import guest_page
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
    path('dashboard/', include('dashboard.urls')),
    path('articles-api/', articles_api.article, name='articles'),
    path('community/', community_views.community, name='community'),
    path('symptoms/', include('symptom_checker.urls')),
    path('generate-blog/', articles_api.gemini_blog_generate, name='gemini_blog_generate'),
#     path('list-models/', articles_api.list_models, name='list_models'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

