
from unittest.mock import MagicMock, patch, PropertyMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework import status
from user.models import PatientProfile, FamilyFriend
from .models import MemoryGameAttempt
from .serializers import FamilyMemorySubmitSerializer
from .views import _norm, _image_url, FamilyMemoryQuestionAPIView, FamilyMemorySubmitAPIView

User = get_user_model()




def make_user(username="testpatient", is_patient=True, password="pass"):
    user_type = "patient" if is_patient else "carer"
    return User.objects.create_user(username=username, password=password, user_type=user_type)




class NormUtilityTests(TestCase):
    def test_lowercases(self):
        self.assertEqual(_norm("ALICE"), "alice")

    def test_strips_whitespace(self):
        self.assertEqual(_norm("  bob  "), "bob")

    def test_collapses_inner_spaces(self):
        self.assertEqual(_norm("john   doe"), "john doe")

    def test_none_returns_empty(self):
        self.assertEqual(_norm(None), "")

    def test_empty_string(self):
        self.assertEqual(_norm(""), "")

    def test_mixed(self):
        self.assertEqual(_norm("  Mary  Jane  "), "mary jane")




class ImageUrlUtilityTests(TestCase):
    def test_no_image_returns_none(self):
        ff = MagicMock()
        ff.image = None
        self.assertIsNone(_image_url(ff))

    def test_url_starting_with_http_returned_as_is(self):
        ff = MagicMock()
        ff.image.url = "https://example.com/photo.jpg"
        self.assertEqual(_image_url(ff), "https://example.com/photo.jpg")

    def test_relative_url_prefixed_with_cloudinary(self):
        ff = MagicMock()
        ff.image.url = "sample/photo.jpg"
        result = _image_url(ff)
        self.assertTrue(result.startswith("https://res.cloudinary.com/"))

    def test_exception_returns_none(self):
        ff = MagicMock()
        type(ff.image).url = PropertyMock(side_effect=Exception("boom"))
        self.assertIsNone(_image_url(ff))




class MemoryGameAttemptModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="patient1",
            password="pass",
            user_type="patient",
        )
        self.patient_profile, _ = PatientProfile.objects.get_or_create(user=self.user)
        self.family_friend = FamilyFriend.objects.create(
            patient_profile=self.patient_profile,
            name="Alice",
            relationship="Sister",
        )

    def _make_attempt(self, **kwargs):
        defaults = dict(
            patient_profile=self.patient_profile,
            family_friend=self.family_friend,
            question_type="name",
            user_answer="alice",
            expected_answer="alice",
            is_correct=True,
        )
        defaults.update(kwargs)
        return MemoryGameAttempt(**defaults)

    def test_str_method(self):
        attempt = self._make_attempt(question_type="name", is_correct=True)
        result = str(attempt)
        self.assertIn("patient1", result)
        self.assertIn("name", result)
        self.assertIn("True", result)

    def test_default_is_correct_false(self):
        attempt = MemoryGameAttempt()
        self.assertFalse(attempt.is_correct)

    def test_ordering_meta(self):
        self.assertEqual(MemoryGameAttempt._meta.ordering, ["-answered_at"])

    def test_question_type_choices(self):
        choices = dict(MemoryGameAttempt.QUESTION_TYPES)
        self.assertIn("name", choices)
        self.assertIn("relationship", choices)



class FamilyMemorySubmitSerializerTests(TestCase):
    def test_valid_answer(self):
        s = FamilyMemorySubmitSerializer(data={"answer": "Alice"})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data["answer"], "Alice")

    def test_blank_answer_is_valid(self):
        s = FamilyMemorySubmitSerializer(data={"answer": ""})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data["answer"], "")

    def test_missing_answer_uses_default(self):
        s = FamilyMemorySubmitSerializer(data={})
        self.assertTrue(s.is_valid())
        self.assertEqual(s.validated_data["answer"], "")

    def test_answer_field_present(self):
        self.assertIn("answer", FamilyMemorySubmitSerializer().fields)




class FamilyMemoryQuestionAPIViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = FamilyMemoryQuestionAPIView.as_view()

    def _make_request(self, user, session_data=None):
        request = self.factory.get("/api/memory/question/")
        request.user = user
        request.session = session_data or {}
        return request

    def test_non_patient_returns_403(self):
        user = MagicMock()
        user.is_patient.return_value = False
        request = self._make_request(user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("memory.views.FamilyFriend.objects.filter")
    def test_no_family_friends_returns_404(self, mock_filter):
        mock_filter.return_value = []
        user = MagicMock()
        user.is_patient.return_value = True
        request = self._make_request(user)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("memory.views.FamilyFriend.objects.filter")
    def test_no_remaining_questions_returns_204(self, mock_filter):
        person = MagicMock()
        person.id = 1
        mock_filter.return_value = [person]
        user = MagicMock()
        user.is_patient.return_value = True
        request = self._make_request(user, session_data={"asked_ids": [1]})
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch("memory.views.random.choice")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_returns_question_for_patient(self, mock_filter, mock_choice):
        person = MagicMock()
        person.id = 42
        person.name = "Alice"
        person.relationship = "Sister"
        person.emergency_contact = False
        person.image = None
        mock_filter.return_value = [person]
        mock_choice.side_effect = [person, "name"]
        user = MagicMock()
        user.is_patient.return_value = True
        request = self._make_request(user, session_data={"asked_ids": []})
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("question", response.data)
        self.assertIn("person", response.data)
        self.assertEqual(response.data["person"]["id"], 42)

    @patch("memory.views.random.choice")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_session_stores_expected_answer(self, mock_filter, mock_choice):
        person = MagicMock()
        person.id = 7
        person.name = "Bob"
        person.relationship = "Brother"
        person.image = None
        mock_filter.return_value = [person]
        mock_choice.side_effect = [person, "name"]
        user = MagicMock()
        user.is_patient.return_value = True
        session = {"asked_ids": []}
        request = self._make_request(user, session_data=session)
        self.view(request)
        self.assertIn("family_memory_q", session)
        self.assertEqual(session["family_memory_q"]["expected"], "bob")

    @patch("memory.views.random.choice")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_relationship_question_type(self, mock_filter, mock_choice):
        person = MagicMock()
        person.id = 3
        person.name = "Carol"
        person.relationship = "Mother"
        person.image = None
        mock_filter.return_value = [person]
        mock_choice.side_effect = [person, "relationship"]
        user = MagicMock()
        user.is_patient.return_value = True
        session = {"asked_ids": []}
        request = self._make_request(user, session_data=session)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(session["family_memory_q"]["expected"], "mother")

    @patch("memory.views.random.choice")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_relationship_falls_back_to_name_when_empty(self, mock_filter, mock_choice):
        person = MagicMock()
        person.id = 5
        person.name = "Dave"
        person.relationship = ""
        person.image = None
        mock_filter.return_value = [person]
        mock_choice.side_effect = [person, "relationship"]
        user = MagicMock()
        user.is_patient.return_value = True
        session = {"asked_ids": []}
        request = self._make_request(user, session_data=session)
        self.view(request)
        self.assertEqual(session["family_memory_q"]["question_type"], "name")




class FamilyMemorySubmitAPIViewTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = FamilyMemorySubmitAPIView.as_view()

    def _make_request(self, user, data, session_data=None):
        request = self.factory.post("/api/memory/submit/", data, format="json")
        request.user = user
        request.session = session_data or {}
        return request

    def test_non_patient_returns_403(self):
        user = MagicMock()
        user.is_patient.return_value = False
        request = self._make_request(user, {"answer": "Alice"})
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_active_question_returns_400(self):
        user = MagicMock()
        user.is_patient.return_value = True
        request = self._make_request(user, {"answer": "Alice"}, session_data={})
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("memory.views.MemoryGameAttempt.objects.create")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_correct_answer_returns_correct_true(self, mock_filter, mock_create):
        ff = MagicMock()
        ff.patient_profile = MagicMock()
        mock_filter.return_value.select_related.return_value.first.return_value = ff
        user = MagicMock()
        user.is_patient.return_value = True
        session = {
            "family_memory_q": {
                "family_friend_id": 1,
                "question_type": "name",
                "expected": "alice",
            }
        }
        request = self._make_request(user, {"answer": "Alice"}, session_data=session)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["correct"])
        self.assertIsNone(response.data["expected"])

    @patch("memory.views.MemoryGameAttempt.objects.create")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_incorrect_answer_returns_expected(self, mock_filter, mock_create):
        ff = MagicMock()
        ff.patient_profile = MagicMock()
        mock_filter.return_value.select_related.return_value.first.return_value = ff
        user = MagicMock()
        user.is_patient.return_value = True
        session = {
            "family_memory_q": {
                "family_friend_id": 1,
                "question_type": "name",
                "expected": "alice",
            }
        }
        request = self._make_request(user, {"answer": "Bob"}, session_data=session)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["correct"])
        self.assertEqual(response.data["expected"], "alice")

    @patch("memory.views.MemoryGameAttempt.objects.create")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_session_cleared_after_submit(self, mock_filter, mock_create):
        ff = MagicMock()
        ff.patient_profile = MagicMock()
        mock_filter.return_value.select_related.return_value.first.return_value = ff
        user = MagicMock()
        user.is_patient.return_value = True
        session = {
            "family_memory_q": {
                "family_friend_id": 1,
                "question_type": "name",
                "expected": "alice",
            }
        }
        request = self._make_request(user, {"answer": "Alice"}, session_data=session)
        self.view(request)
        self.assertNotIn("family_memory_q", session)

    @patch("memory.views.MemoryGameAttempt.objects.create")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_attempt_created_on_submit(self, mock_filter, mock_create):
        ff = MagicMock()
        ff.patient_profile = MagicMock()
        mock_filter.return_value.select_related.return_value.first.return_value = ff
        user = MagicMock()
        user.is_patient.return_value = True
        session = {
            "family_memory_q": {
                "family_friend_id": 1,
                "question_type": "relationship",
                "expected": "sister",
            }
        }
        request = self._make_request(user, {"answer": "sister"}, session_data=session)
        self.view(request)
        mock_create.assert_called_once()

    @patch("memory.views.MemoryGameAttempt.objects.create")
    @patch("memory.views.FamilyFriend.objects.filter")
    def test_no_attempt_created_when_ff_not_found(self, mock_filter, mock_create):
        mock_filter.return_value.select_related.return_value.first.return_value = None
        user = MagicMock()
        user.is_patient.return_value = True
        session = {
            "family_memory_q": {
                "family_friend_id": 999,
                "question_type": "name",
                "expected": "alice",
            }
        }
        request = self._make_request(user, {"answer": "alice"}, session_data=session)
        response = self.view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_create.assert_not_called()
