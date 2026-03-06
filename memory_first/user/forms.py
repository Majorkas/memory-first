from allauth.account.forms import SignupForm
from django.contrib.auth import get_user_model

User = get_user_model()


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
