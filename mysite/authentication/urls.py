from django.urls import path
from . import views

urlpatterns = [
    path('', views.guest_page, name="guest_page"),
    path('home/', views.home, name="home"),
    path('login/', views.login_page, name='login_page'),
    path('register/', views.register_page, name='register'),
]
