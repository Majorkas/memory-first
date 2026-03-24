import random
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from user.models import FamilyFriend
from .serializers import FamilyMemorySubmitSerializer
from .models import MemoryGameAttempt


def _norm(text: str) -> str:
    #helper to normalise answers stripping of extra spaces and making lowercase
    return " ".join((text or "").strip().lower().split())


def _image_url(ff: FamilyFriend):
    #helper to get ff image
    if not ff.image:
        return None
    try:
        url = ff.image.url
        return url if url.startswith("http") else f"https://res.cloudinary.com/{url}"
    except Exception:
        return None


class MemoryGamePageView(LoginRequiredMixin, TemplateView):
    #View for the Game
    template_name = "memory/game.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        count = FamilyFriend.objects.filter(patient_profile__user=self.request.user).count()
        context["total_questions"] = min(count, 10)
        # Reset session for a fresh game
        self.request.session.pop("asked_ids", None)
        return context


class FamilyMemoryQuestionAPIView(APIView):
    #Endpoint to serve one memory game question per request aslong as the user is a patient
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_patient():
            return Response({"detail": "Patients only."}, status=status.HTTP_403_FORBIDDEN)

        people = list(FamilyFriend.objects.filter(patient_profile__user=request.user))
        if not people:
            return Response({"detail": "No family/friend records found."}, status=status.HTTP_404_NOT_FOUND)

        asked = request.session.get("asked_ids", [])
        remaining = [p for p in people if p.id not in asked]

        if not remaining:
            return Response({"detail": "No more questions."}, status=status.HTTP_204_NO_CONTENT)

        person = random.choice(remaining)
        asked.append(person.id)
        request.session["asked_ids"] = asked

        question_type = random.choice(["name", "relationship"])
        if question_type == "relationship" and not person.relationship:
            question_type = "name"

        expected_answer = person.name if question_type == "name" else person.relationship
        request.session["family_memory_q"] = {
            "family_friend_id": person.id,
            "question_type": question_type,
            "expected": _norm(expected_answer),
        }

        prompt = (
            "What is this person's name?"
            if question_type == "name"
            else "What is this person's relationship to you?"
        )

        return Response(
            {
                "question": prompt,
                "question_type": question_type,
                "person": {
                    "id": person.id,
                    "image": _image_url(person),
                    "name": person.name,
                    "relationship": person.relationship,
                    "emergency_contact": person.emergency_contact,
                },
            }
        )


class FamilyMemorySubmitAPIView(APIView):
    #Answer checking endpoint rejecting non-patient users again, if all is well submits the MemoryGameAttempt to db
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if not request.user.is_patient():
            return Response({"detail": "Patients only."}, status=status.HTTP_403_FORBIDDEN)

        state = request.session.get("family_memory_q")
        if not state:
            return Response({"detail": "No active question."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = FamilyMemorySubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        raw_answer = serializer.validated_data.get("answer", "")
        user_answer = _norm(raw_answer)
        expected = state["expected"]
        correct = user_answer == expected

        ff = FamilyFriend.objects.filter(
            id=state.get("family_friend_id"),
            patient_profile__user=request.user,
        ).select_related("patient_profile").first()

        if ff:
            MemoryGameAttempt.objects.create(
                patient_profile=ff.patient_profile,
                family_friend=ff,
                question_type=state["question_type"],
                user_answer=raw_answer,
                expected_answer=expected,
                is_correct=correct,
            )

        request.session.pop("family_memory_q", None)

        return Response(
            {
                "correct": correct,
                "question_type": state["question_type"],
                "expected": None if correct else expected,
            }
        )
