from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import StudentProfile

PROFILE_FIELDS = [
    "full_name",
    "date_of_birth",
    "gender",
    "phone_number",
    "institution",
    "grade_or_class",
    "student_id",
]


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=200)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.ChoiceField(required=False, choices=StudentProfile.Gender.choices)
    phone_number = forms.CharField(required=False, max_length=30)
    institution = forms.CharField(required=False, max_length=200)
    grade_or_class = forms.CharField(required=False, max_length=100)
    student_id = forms.CharField(required=False, max_length=100)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", *PROFILE_FIELDS, "password1", "password2")

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                **{
                    f: self.cleaned_data.get(f) or ""
                    for f in PROFILE_FIELDS
                    if f != "date_of_birth"
                },
                date_of_birth=self.cleaned_data.get("date_of_birth"),
            )
        return user


class ProfileForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = StudentProfile
        fields = PROFILE_FIELDS
        widgets = {"date_of_birth": forms.DateInput(attrs={"type": "date"})}
