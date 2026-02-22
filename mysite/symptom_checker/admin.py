from django.contrib import admin
from .models import BodyArea, Symptom, Cause, Disease, Doctor, SymptomReport

admin.site.register(BodyArea)
admin.site.register(Symptom)
admin.site.register(Cause)
admin.site.register(Disease)
admin.site.register(Doctor)
admin.site.register(SymptomReport)
