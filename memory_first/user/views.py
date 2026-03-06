from allauth.account.views import SignupView
from .models import CUser
from .forms import PatientSignupForm, CarerSignupForm

class PatientSignupView(SignupView):
    form_class = PatientSignupForm


class CarerSignupView(SignupView):
    form_class = CarerSignupForm
