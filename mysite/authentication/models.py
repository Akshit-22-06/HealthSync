from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    ROLE_DOCTOR = "doctor"
    ROLE_USER = "user"

    ROLE_CHOICES = [
        (ROLE_DOCTOR, "Doctor"),
        (ROLE_USER, "User"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    is_approved = models.BooleanField(default=False)

    # Doctor fields
    license_number = models.CharField(max_length=100, blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    verification_document = models.FileField(upload_to="doctor_docs/", blank=True, null=True)
    def __str__(self):
        return self.username