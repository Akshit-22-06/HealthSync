from django.urls import path
from . import views

urlpatterns = [
    path("", views.start, name="symptom_home"),
    path("question/", views.question, name="question"),
    path("result/", views.result_page, name="result_page"),
    path("reset/", views.reset_flow, name="reset_flow"),
    path("location-suggest/", views.location_suggest, name="location_suggest"),
]
