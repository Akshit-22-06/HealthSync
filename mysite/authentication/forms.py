from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

User = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={"id": "email", "name": "email", "placeholder": "Enter email"}
        ),
    )
    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
            "role",
            "license_number",
            "specialization",
            "verification_document",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"id": "username", "name": "username", "placeholder": "Enter username"}
        )
        self.fields["password1"].widget.attrs.update(
            {"id": "password", "name": "password1", "placeholder": "Enter password"}
        )
        self.fields["password2"].widget.attrs.update(
            {
                "id": "confirm_password",
                "name": "password2",
                "placeholder": "Confirm password",
            }
        )
        self.fields["role"].widget.attrs.update(
            {"id": "role", "name": "role", "placeholder": "Select role"}
        )
        if "license_number" in self.fields:
            self.fields["license_number"].widget.attrs.update(
                {"placeholder": "Medical license number"}
            )

        if "specialization" in self.fields:
            self.fields["specialization"].widget.attrs.update(
                {"placeholder": "e.g. Cardiology, General Medicine"}
            )
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]

        if user.role == "doctor":
            # Pending doctors can log in and use user features while approval is pending.
            user.is_active = True
            user.is_approved = False
        else:
            user.is_active = True
            user.is_approved = True

        if commit:
            user.save()
            # Group syncing handled by signal

        return user
