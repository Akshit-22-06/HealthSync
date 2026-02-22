from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def assign_user_group(sender, instance, **kwargs):

    if instance.role:
        group_name = instance.role.capitalize()
        group, _ = Group.objects.get_or_create(name=group_name)

        instance.groups.clear()
        instance.groups.add(group)

    # 🔥 Auto activate doctor when approved
    if instance.role == "doctor" and instance.is_approved:
        if not instance.is_active:
            instance.is_active = True
            instance.save(update_fields=["is_active"])