from django.urls import path, include
from .views import CarerSignupView, PatientSignupView

urlpatterns = [
    path("accounts/signup/carer/", CarerSignupView.as_view(), name="carer_signup"),
    path("accounts/signup/patient/", PatientSignupView.as_view(), name="patient_signup"),
    path("accounts/", include("allauth.urls")),
]
