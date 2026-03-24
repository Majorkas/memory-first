from django.test import TestCase
from .models import CUser, PatientCarerRelationship,PatientProfile,CarerProfile
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from django.urls import reverse
from unittest.mock import MagicMock, patch
from .views import PatientSignupView, CarerSignupView
from .forms import PatientSignupForm, CarerSignupForm

class CUserModelTests(TestCase):
    # Tests the creation of the CUsers and all their helpers
    @classmethod
    def setUpTestData(cls):
          cls.carer = CUser.objects.create_user(username='C1', password='12345')
          cls.patient = CUser.objects.create_user(username='P1', password='12345', user_type='patient')

    def test_user_type(self):
         patient = CUser.objects.get(username='P1')
         carer = CUser.objects.get(username='C1')
         expected_patient_user_type = f'{patient.user_type}'
         expected_carer_user_type = f'{carer.user_type}'
         self.assertEqual(expected_patient_user_type, 'patient')
         self.assertEqual(expected_carer_user_type, f'carer')

    def test_relationship(self):
        patient = CUser.objects.get(username='P1')
        carer = CUser.objects.get(username='C1')

        rel = PatientCarerRelationship.objects.get_or_create(patient = patient, carer = carer)
        self.assertEqual(str(rel[0]), f'{self.carer.username} cares for {self.patient.username}')

    def test_helpers(self):
        patient = CUser.objects.get(username='P1')
        carer = CUser.objects.get(username='C1')
        rel = PatientCarerRelationship.objects.get_or_create(patient = patient, carer = carer)

        self.assertEqual(patient.is_patient(), True)
        self.assertEqual(carer.is_carer(), True)
        self.assertEqual(patient.is_carer(), False)
        self.assertEqual(carer.is_patient(), False)
        self.assertEqual(patient.get_carers()[0], carer)
        self.assertEqual(carer.get_patients()[0], patient)

class AutoCreatedProfilesTests(TestCase):
    # Tests the profile auto create and that users cant have multiple profiles created
    def test_patient_profile_is_created_for_patient_user(self):
        user = CUser.objects.create_user(
            username="patient_auto",
            password="pass12345",
            user_type=CUser.User_type.PATIENT,
        )


        self.assertTrue(PatientProfile.objects.filter(user=user).exists())

        profile = PatientProfile.objects.get(user=user)
        self.assertEqual(str(profile), "PatientProfile(patient_auto)")

    def test_carer_profile_is_auto_created_for_carer_user(self):
        user = CUser.objects.create_user(
            username="carer_auto",
            password="pass12345",
            user_type=CUser.User_type.CARER,
        )

        self.assertTrue(CarerProfile.objects.filter(user=user).exists())

        profile = CarerProfile.objects.get(user=user)
        self.assertEqual(str(profile), "CarerProfile(carer_auto)")

    def test_cannot_create_second_patient_profile_for_same_user(self):
        user = CUser.objects.create_user(
            username="patient_dup",
            password="pass12345",
            user_type=CUser.User_type.PATIENT,
        )


        with self.assertRaises(IntegrityError):
            PatientProfile.objects.create(user=user)

    def test_cannot_create_second_carer_profile_for_same_user(self):
        user = CUser.objects.create_user(
            username="carer_dup",
            password="pass12345",
            user_type=CUser.User_type.CARER,
        )

        with self.assertRaises(IntegrityError):
            CarerProfile.objects.create(user=user)

class ProfileValidationTests(TestCase):
    #Checks the .clean() on the profile models
    def test_patient_profile_clean_rejects_non_patient_user(self):
        user = CUser.objects.create_user(
            username="carer_for_patient_profile",
            password="pass12345",
            user_type=CUser.User_type.CARER,
        )

        profile = PatientProfile(user=user)

        with self.assertRaises(ValidationError):
            profile.clean()

    def test_carer_profile_clean_rejects_non_carer_user(self):
        user = CUser.objects.create_user(
            username="patient_for_carer_profile",
            password="pass12345",
            user_type=CUser.User_type.PATIENT,
        )

        profile = CarerProfile(user=user)

        with self.assertRaises(ValidationError):
            profile.clean()


class SignupViewTests(TestCase):
    def test_patient_signup_view_form_class(self):
        self.assertIs(PatientSignupView.form_class, PatientSignupForm)

    def test_carer_signup_view_form_class(self):
        self.assertIs(CarerSignupView.form_class, CarerSignupForm)


class DashboardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.carer = CUser.objects.create_user(
            username="dash_carer",
            password="pass12345",
            user_type=CUser.User_type.CARER,
        )
        cls.patient = CUser.objects.create_user(
            username="dash_patient",
            password="pass12345",
            user_type=CUser.User_type.PATIENT,
        )
        PatientCarerRelationship.objects.create(patient=cls.patient, carer=cls.carer)

    def test_get_dashboard_as_carer(self):
        self.client.force_login(self.carer)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_carer"])
        self.assertFalse(response.context["is_patient"])
        self.assertIn(self.patient, response.context["patients"])

    def test_get_dashboard_as_patient(self):
        self.client.force_login(self.patient)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_patient"])
        self.assertFalse(response.context["is_carer"])
        self.assertIn(self.carer, response.context["carers"])

    @patch("user.views.CarerCreatesPatientUserForm")
    def test_post_create_patient_as_carer_success(self, mock_form_cls):
        self.client.force_login(self.carer)

        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form.cleaned_data = {
            "username": "new_patient_1",
            "email": "newp@example.com",
            "password1": "pass12345",
        }
        mock_form_cls.return_value = mock_form

        response = self.client.post(
            reverse("dashboard"),
            {"action": "create_patient"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        created_patient = CUser.objects.get(username="new_patient_1")
        self.assertEqual(created_patient.user_type, CUser.User_type.PATIENT)
        self.assertTrue(
            PatientCarerRelationship.objects.filter(
                patient=created_patient, carer=self.carer
            ).exists()
        )

    @patch("user.views.CarerProfileForm")
    def test_post_edit_carer_profile_success(self, mock_form_cls):
        self.client.force_login(self.carer)

        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form_cls.return_value = mock_form

        response = self.client.post(
            reverse("dashboard"),
            {"action": "edit_carer_profile"},
        )

        self.assertRedirects(response, reverse("dashboard"))
        mock_form.save.assert_called_once()

    def test_post_edit_patient_profile_for_unlinked_patient_forbidden(self):
        other_patient = CUser.objects.create_user(
            username="unlinked_patient",
            password="pass12345",
            user_type=CUser.User_type.PATIENT,
        )
        self.client.force_login(self.carer)

        response = self.client.post(
            reverse("dashboard"),
            {
                "action": "edit_patient_profile",
                "patient_id": other_patient.id,
            },
        )

        self.assertEqual(response.status_code, 403)

    @patch("user.views.PatientProfileForm")
    def test_post_edit_patient_profile_success(self, mock_form_cls):
        self.client.force_login(self.carer)

        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_form_cls.return_value = mock_form

        response = self.client.post(
            reverse("dashboard"),
            {
                "action": "edit_patient_profile",
                "patient_id": self.patient.id,
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        mock_form.save.assert_called_once()


class CarerPatientDetailViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.carer = CUser.objects.create_user(
            username="detail_carer",
            password="pass12345",
            user_type=CUser.User_type.CARER,
        )
        cls.patient = CUser.objects.create_user(
            username="detail_patient",
            password="pass12345",
            user_type=CUser.User_type.PATIENT,
        )
        cls.non_carer_user = CUser.objects.create_user(
            username="detail_non_carer",
            password="pass12345",
            user_type=CUser.User_type.PATIENT,
        )
        cls.unlinked_carer = CUser.objects.create_user(
            username="detail_unlinked_carer",
            password="pass12345",
            user_type=CUser.User_type.CARER,
        )
        PatientCarerRelationship.objects.create(patient=cls.patient, carer=cls.carer)

    def _url(self, patient_id):
        return reverse("carer_patient_detail", kwargs={"patient_id": patient_id})

    def test_get_requires_carer(self):
        self.client.force_login(self.non_carer_user)
        response = self.client.get(self._url(self.patient.id))
        self.assertEqual(response.status_code, 403)

    def test_get_requires_linked_carer(self):
        self.client.force_login(self.unlinked_carer)
        response = self.client.get(self._url(self.patient.id))
        self.assertEqual(response.status_code, 403)

    def test_get_linked_carer_success(self):
        self.client.force_login(self.carer)
        response = self.client.get(self._url(self.patient.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["patient"], self.patient)

    @patch("user.views.get_object_or_404")
    def test_post_delete_family_friend(self, mock_get_object_or_404):
        self.client.force_login(self.carer)

        fake_ff = MagicMock()
        mock_get_object_or_404.side_effect = [self.patient, fake_ff]

        response = self.client.post(
            self._url(self.patient.id),
            {"action": "delete_family_friend", "family_friend_id": 1},
        )

        self.assertRedirects(response, self._url(self.patient.id), fetch_redirect_response=False)
        fake_ff.delete.assert_called_once()

    @patch("user.views.FamilyFriendForm")
    def test_post_add_family_friend_success(self, mock_form_cls):
        self.client.force_login(self.carer)

        mock_form = MagicMock()
        mock_form.is_valid.return_value = True

        fake_obj = MagicMock()
        mock_form.save.return_value = fake_obj

        mock_form_cls.return_value = mock_form

        response = self.client.post(
            self._url(self.patient.id),
            {"action": "add_family_friend"},
        )

        self.assertRedirects(response, self._url(self.patient.id))
        mock_form.save.assert_called_once_with(commit=False)
        fake_obj.save.assert_called_once()

    @patch("user.views.FamilyFriendForm")
    @patch("user.views.get_object_or_404")
    def test_post_edit_family_friend_success(self, mock_get_object_or_404, mock_form_cls):
        self.client.force_login(self.carer)

        fake_ff = MagicMock()
        mock_get_object_or_404.side_effect = [self.patient, fake_ff]

        mock_form = MagicMock()
        mock_form.is_valid.return_value = True

        updated_obj = MagicMock()
        mock_form.save.return_value = updated_obj
        mock_form_cls.return_value = mock_form

        response = self.client.post(
            self._url(self.patient.id),
            {"action": "edit_family_friend", "family_friend_id": 123},
        )

        self.assertRedirects(response, self._url(self.patient.id), fetch_redirect_response=False)
        mock_form.save.assert_called_once_with(commit=False)
        updated_obj.save.assert_called_once()
