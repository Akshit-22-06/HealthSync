from django.db import models
from django.conf import settings


class BodyArea(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Symptom(models.Model):
    name = models.CharField(max_length=200)
    body_area = models.ForeignKey(BodyArea, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Cause(models.Model):
    name = models.CharField(max_length=200)
    symptoms = models.ManyToManyField(Symptom)

    def __str__(self):
        return self.name


class Disease(models.Model):
    name = models.CharField(max_length=200)
    causes = models.ManyToManyField(Cause)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Doctor(models.Model):
    name = models.CharField(max_length=200)
    specialization = models.CharField(max_length=200)
    city = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.city}"


class SymptomReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    symptoms = models.ManyToManyField(Symptom)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report {self.id}"
