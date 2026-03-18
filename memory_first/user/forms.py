from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth import get_user_model
from .models import PatientProfile, FamilyFriend, CarerProfile

User = get_user_model()


class FamilyFriendForm(forms.ModelForm):
    class Meta:
        model = FamilyFriend
        exclude = ["patient_profile"]


class PatientSignupForm(SignupForm):
    def save(self, request):
        user = super().save(request)
        if user.user_type != User.User_type.PATIENT:
            user.user_type = User.User_type.PATIENT
            user.save(update_fields=["user_type"])
        return user


class CarerSignupForm(SignupForm):
    def save(self, request):
        user = super().save(request)
        if user.user_type != User.User_type.CARER:
            user.user_type = User.User_type.CARER
            user.save(update_fields=["user_type"])
        return user

class CarerCreatesPatientUserForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=True)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        if User.objects.filter(username=cleaned.get("username")).exists():
            self.add_error("username", "Username is already taken.")
        return cleaned

class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ["patient_profile_picture", "date_of_birth", "address"]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }

class CarerProfileForm(forms.ModelForm):
    class Meta:
        model = CarerProfile
        fields = ["employer", "phone", "carer_profile_picture"]
