from django.urls import path, include
from django.views.generic import TemplateView
from .views import CarerSignupView, PatientSignupView

urlpatterns = [
    path("accounts/signup/",TemplateView.as_view(template_name="account/signup_choice.html"),name="account_signup",),
    path("accounts/signup/carer/", CarerSignupView.as_view(), name="carer_signup"),
    path("accounts/signup/patient/", PatientSignupView.as_view(), name="patient_signup"),
    path("accounts/", include("allauth.urls")),
]
