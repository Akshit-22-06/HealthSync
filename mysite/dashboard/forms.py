from django import forms
from .models import HealthLog


class HealthLogForm(forms.ModelForm):

    class Meta:
        model = HealthLog
        fields = [
            'sleep_hours',
            'water_liters',
            'mood',
            'exercise_minutes'
        ]

        widgets = {
            'sleep_hours': forms.NumberInput(attrs={
                'min': 0,
                'max': 24,
                'step': 0.1,
                'placeholder': 'Hours slept (e.g. 7.5)'
            }),

            'water_liters': forms.NumberInput(attrs={
                'min': 0,
                'max': 10,
                'step': 0.1,
                'placeholder': 'Water in liters (e.g. 2.5)'
            }),

            'exercise_minutes': forms.NumberInput(attrs={
                'min': 0,
                'max': 300,
                'placeholder': 'Exercise minutes (e.g. 45)'
            }),
        }

        labels = {
            'sleep_hours': 'Sleep (Hours)',
            'water_liters': 'Water Intake (Liters)',
            'mood': 'Mood (1-5)',
            'exercise_minutes': 'Exercise (Minutes)',
        }