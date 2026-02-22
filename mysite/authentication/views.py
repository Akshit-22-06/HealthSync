from django.shortcuts import render,redirect
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistrationForm
from .decorators import doctor_approved_required
# Create your views here.
@login_required(login_url='/login/')
def home(request):
    return render(request, 'home.html')

def login_page(request):
    form = AuthenticationForm(request, data=request.POST or None)
    form.fields["username"].widget.attrs.update({"id": "username", "placeholder": "Enter username"})
    form.fields["password"].widget.attrs.update({"id": "password", "placeholder": "Enter password"})
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = User.objects.filter(username=username).first()

        if user and user.check_password(password):
            # Inactive account
            if not user.is_active:
                messages.error(request, "Your account is inactive.")
                return redirect("login")

            login(request, user)

            if user.role == "doctor" and not user.is_approved:
                messages.info(
                    request,
                    "Your doctor approval request is pending. You can use user features for now."
                )
            return redirect("home")

        messages.error(request, "Invalid username or password.")

    return render(request, 'authentication/login.html', {"form": form})

# Define a view function for the registration page
def register_page(request):
    form = RegistrationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()

            if user.role == "doctor":
                messages.info(
                    request,
                    "Doctor registration submitted successfully. Please wait for admin approval."
                )
            else:
                messages.success(request, "Account created successfully! You can now login.")

            return redirect('login')

    return render(request, 'authentication/register.html', {"form": form})


def guest_page(request):
    return render(request, 'guest.html')


@login_required(login_url="/login/")
def doctor_request_status(request):
    if request.user.role != "doctor":
        return redirect("home")

    return render(
        request,
        "authentication/doctor_request_status.html",
        {"is_approved": request.user.is_approved},
    )


@doctor_approved_required
def doctor_portal(request):
    return render(request, "authentication/doctor_portal.html")
