from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import ProfileForm, RegistrationForm
from .models import StudentProfile


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("accounts:dashboard")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    obj, _ = StudentProfile.objects.get_or_create(
        user=request.user,
        defaults={"full_name": request.user.get_full_name() or request.user.username},
    )
    initial = {"email": request.user.email}
    form = ProfileForm(request.POST or None, instance=obj, initial=initial)
    if request.method == "POST" and form.is_valid():
        form.save()
        request.user.email = form.cleaned_data["email"]
        request.user.save(update_fields=["email"])
        return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def dashboard(request):
    from exams.models import Attempt
    from exams.services import finalize_attempt

    expired = Attempt.objects.filter(
        student=request.user, status=Attempt.Status.IN_PROGRESS, expires_at__lte=timezone.now()
    )
    for attempt in expired:
        finalize_attempt(attempt, expired=True)
    qs = Attempt.objects.filter(student=request.user).select_related("exam").order_by("-started_at")
    return render(
        request,
        "accounts/dashboard.html",
        {"page_obj": Paginator(qs, 10).get_page(request.GET.get("page"))},
    )
