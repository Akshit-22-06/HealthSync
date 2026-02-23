from django.db import models
from django.contrib.auth import get_user_model
User = get_user_model()
STATUS_CHOICES = [
    ('pending', 'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]


# Create your models here.
class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="articles")
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_articles")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    is_published = models.BooleanField(default=False)