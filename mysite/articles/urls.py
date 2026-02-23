from django.urls import path
from . import views

urlpatterns = [
    path('', views.article, name='articles'),
    path("my-articles/", views.my_articles, name="my_articles"),
    path("review-queue/", views.review_queue, name="review_queue"),
    path("approve/<int:id>/", views.approve_article, name="approve_article"),
    path("reject/<int:id>/", views.reject_article, name="reject_article"),
    path("post-article/", views.post_article, name="post_article"),
    path("delete/<int:id>/", views.delete_article, name="delete_article"),
]