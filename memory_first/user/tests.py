from django.test import TestCase
from .models import CUser, PatientCarerRelationship,PatientProfile,CarerProfile
from django.core.exceptions import ValidationError
from django.db import IntegrityError

class CUserModelTests(TestCase):
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
