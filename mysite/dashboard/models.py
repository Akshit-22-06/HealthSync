from django.db import models
from django.conf import settings


class HealthLog(models.Model):

    MOOD_CHOICES = [
        (1, "Very Bad"),
        (2, "Bad"),
        (3, "Okay"),
        (4, "Good"),
        (5, "Excellent"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    date = models.DateField(auto_now_add=True)

    sleep_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1
    )

    water_liters = models.DecimalField(
        max_digits=4,
        decimal_places=1
    )

    mood = models.IntegerField(
        choices=MOOD_CHOICES
    )

    exercise_minutes = models.IntegerField()

    def __str__(self):
        return f"{self.user.username} - {self.date}"