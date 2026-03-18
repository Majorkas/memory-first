from allauth.account.views import SignupView
from .models import CUser, PatientProfile, PatientCarerRelationship, FamilyFriend, CarerProfile
from .forms import PatientSignupForm, CarerSignupForm, PatientProfileForm, CarerCreatesPatientUserForm, FamilyFriendForm, CarerProfileForm
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.core.exceptions import PermissionDenied




class PatientSignupView(SignupView):
    #Signup View for a Patient Account
    form_class = PatientSignupForm


class CarerSignupView(SignupView):
    #Signup View for a Carer Account
    form_class = CarerSignupForm


class DashboardView(LoginRequiredMixin, View):
    template_name = "dashboard/dashboard.html"

    def get(self, request):
        #On Get runs build context and returns it for use on the template
        context = self._build_context(request)
        return render(request, self.template_name, context)

    def post(self, request):
        #On Post also builds context then checks the action on the form if update_patient_profile goes down that path elif create_patient goes down that path both using get_or_create as a precaution incase the signals fail
        user = request.user
        context = self._build_context(request)
        action = request.POST.get("action")



        if user.is_carer() and action == "create_patient":
            #Action to Create a Patient User only if current User is Carer
            form = CarerCreatesPatientUserForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    patient_user = CUser.objects.create_user(
                        username=form.cleaned_data["username"],
                        email=form.cleaned_data["email"],
                        password=form.cleaned_data["password1"],
                        user_type=CUser.User_type.PATIENT,
                    )
                    PatientProfile.objects.get_or_create(user=patient_user)
                    PatientCarerRelationship.objects.get_or_create(
                        patient=patient_user,
                        carer=user,
                        defaults={"is_active": True},
                    )
                messages.success(request, "Patient user created and linked.")
                return redirect("dashboard")
            context["create_patient_form"] = form

        elif user.is_carer() and action == "edit_carer_profile":
            #Action to edit Carer profile only if current User is a Carer
            profile, _ = CarerProfile.objects.get_or_create(user=user)
            form = CarerProfileForm(request.POST, request.FILES, instance=profile)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated.")
                return redirect("dashboard")

            context["edit_carer_profile_errors"] = form.errors

        elif user.is_carer() and action == "edit_patient_profile":
            #Action to edit Patient Profile only if User is Carer
            patient = get_object_or_404(CUser, id=request.POST.get("patient_id"), user_type=CUser.User_type.PATIENT)

            is_linked = PatientCarerRelationship.objects.filter(carer=user, patient=patient).exists()
            if not is_linked:
                raise PermissionDenied("You are not linked to this patient.")

            profile, _ = PatientProfile.objects.get_or_create(user=patient)
            form = PatientProfileForm(request.POST, request.FILES, instance=profile)

            if form.is_valid():
                form.save()
                messages.success(request, "Patient profile updated.")
                return redirect("dashboard")

            context["edit_patient_profile_errors_for_id"] = patient.id
            context["edit_patient_profile_errors"] = form.errors

        return render(request, self.template_name, context)

    def _build_context(self, request):
        #Gathers information from the db for use on the templates
        user = request.user

        #initialize the context to stop errors due to missing content
        carer_profile = None
        create_patient_form = None
        family_friends_page = None
        patient_profile = None
        carers = []
        patients = []

        is_patient = (str(user.user_type).lower() == "patient")
        is_carer = (str(user.user_type).lower() == "carer")

        if is_patient:
            #checks if user is a patient and if so gathers all the patient related context and paginates the family friend context

            patient_profile, _ = PatientProfile.objects.get_or_create(user=user)

            family_friends_qs = patient_profile.family_friend.all().order_by("name")
            ff_paginator = Paginator(family_friends_qs, 6)
            family_friends_page = ff_paginator.get_page(request.GET.get("ff_page"))

            carers = user.get_carers().select_related("carer_profile").distinct()


        elif is_carer:
            #checks if user is a carer and gathers all related context
            carer_profile, _ = CarerProfile.objects.get_or_create(user=user)
            patients = user.get_patients().select_related("patient_profile").distinct()
            create_patient_form = CarerCreatesPatientUserForm()

        return {
            "is_patient": is_patient,
            "is_carer": is_carer,
            "family_friends_page": family_friends_page,
            "carers": carers,
            "patients": patients,
            "patient_profile": patient_profile,
            "create_patient_form": create_patient_form,
            "carer_profile": carer_profile,
        }




class CarerPatientDetailView(LoginRequiredMixin, View):
    #View for displaying the in depth Patient details to Carer
    template_name = "dashboard/carer_patient_detail.html"

    def get(self, request, patient_id):
        #On Get Checks if the current user is a Carer, gets the patient by the patient id then checks to make sure the Carer is the Patients Carer
        if not request.user.is_carer():
            raise PermissionDenied("Only carers can access this page.")

        patient = get_object_or_404(CUser, id=patient_id, user_type=CUser.User_type.PATIENT)

        is_linked = PatientCarerRelationship.objects.filter(
            carer=request.user,
            patient=patient,
        ).exists()
        if not is_linked:
            raise PermissionDenied("You are not linked to this patient.")

        patient_profile, _ = PatientProfile.objects.get_or_create(user=patient)
        family_friend_form = FamilyFriendForm()

        return render(
            request,
            self.template_name,
            {
                "patient": patient,
                "patient_profile": patient_profile,
                "family_friends": patient_profile.family_friend.all().order_by("name"),
                "family_friend_form": family_friend_form,
                "edit_form_errors_for_id": None,
                "edit_form_errors": None,
            },
        )

    def post(self, request, patient_id):
        #On Post checks if Current User is a Carer, gets the Patient by their ID checks they are linked then if all okay will check the form and save it adding the family friend
        if not request.user.is_carer():
            raise PermissionDenied("Only carers can access this page.")

        patient = get_object_or_404(CUser, id=patient_id, user_type=CUser.User_type.PATIENT)

        is_linked = PatientCarerRelationship.objects.filter(
            carer=request.user,
            patient=patient,
        ).exists()
        if not is_linked:
            raise PermissionDenied("You are not linked to this patient.")

        patient_profile, _ = PatientProfile.objects.get_or_create(user=patient)
        edit_form_errors_for_id = None
        edit_form_errors = None


        action = request.POST.get("action")
        #gets form action and performs correct action depending on it



        if action == "delete_family_friend":
            #Action for deleting
            ff = get_object_or_404(
                FamilyFriend,
                id=request.POST.get("family_friend_id"),
                patient_profile=patient_profile,
            )
            ff.delete()
            messages.success(request, "Family/Friend removed.")
            return redirect("carer_patient_detail", patient_id=patient.id)

        if action == "edit_family_friend":
            #Action for editing
            ff = get_object_or_404(
                FamilyFriend,
                id=request.POST.get("family_friend_id"),
                patient_profile=patient_profile,
            )
            edit_form = FamilyFriendForm(request.POST, request.FILES, instance=ff)
            if edit_form.is_valid():
                updated = edit_form.save(commit=False)
                updated.patient_profile = patient_profile
                updated.save()
                messages.success(request, "Family/Friend updated.")
                return redirect("carer_patient_detail", patient_id=patient.id)
            edit_form_errors_for_id = ff.id
            edit_form_errors = edit_form.errors

        if action == "add_family_friend":
            #Action for creating new FF
            family_friend_form = FamilyFriendForm(request.POST, request.FILES)

            if family_friend_form.is_valid():
                ff = family_friend_form.save(commit=False)
                ff.patient_profile = patient_profile
                ff.save()
                messages.success(request, "Family/Friend added.")
                return redirect("carer_patient_detail", patient_id=patient.id)

        return render(
            request,
            self.template_name,
            {
                "patient": patient,
                "patient_profile": patient_profile,
                "family_friends": patient_profile.family_friend.all().order_by("name"),
                "family_friend_form": family_friend_form,
                "edit_form_errors_for_id": edit_form_errors_for_id,
                "edit_form_errors": edit_form_errors,
            },
        )
