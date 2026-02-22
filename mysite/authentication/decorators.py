from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def doctor_approved_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.role != "doctor":
            messages.error(request, "Doctor access only.")
            return redirect("home")

        if not request.user.is_approved:
            messages.info(request, "Your doctor approval request is still pending.")
            return redirect("doctor_request_status")

        return view_func(request, *args, **kwargs)

    return _wrapped_view
