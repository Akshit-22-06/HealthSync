from django.urls import path
from . import views

urlpatterns = [
    path("", views.symptom_home, name="symptom_home"),
    path("question/<int:q_index>/", views.symptom_question, name="symptom_question"),
    path("result/", views.symptom_result, name="symptom_result"),
]
