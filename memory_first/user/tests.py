from django.test import TestCase, Client
from django.urls import reverse
from .models import CUser, PatientCarerRelationship

class PostModelTests(TestCase):
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
