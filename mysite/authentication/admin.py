# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import CustomUser


# class CustomUserAdmin(UserAdmin):
#     model = CustomUser
#     list_display = ("username", "email", "role", "is_staff", "is_superuser")
#     list_filter = ("role", "is_staff", "is_superuser")



from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        "username",
        "email",
        "role",
        "is_approved",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "is_approved",
        "is_active",
        "is_staff",
    )

    search_fields = ("username", "email", "license_number", "specialization")

    fieldsets = UserAdmin.fieldsets + (
        ("Role & Approval", {
            "fields": ("role", "is_approved")
        }),
        ("Doctor Information", {
            "fields": ("license_number", "specialization", "verification_document"),
        }),
    )

    actions = ["approve_doctors"]

    def approve_doctors(self, request, queryset):
        doctors = queryset.filter(role="doctor")
        doctors.update(is_approved=True, is_active=True)

    approve_doctors.short_description = "Approve selected doctors"