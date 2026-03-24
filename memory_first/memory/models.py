from django.db import models




from django.db import models
from user.models import PatientProfile, FamilyFriend


class MemoryGameAttempt(models.Model):
    QUESTION_TYPES = (
        ("name", "Name"),
        ("relationship", "Relationship"),
    )

    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="memory_attempts",
    )
    family_friend = models.ForeignKey(
        FamilyFriend,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memory_attempts",
    )
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    user_answer = models.CharField(max_length=100, blank=True)
    expected_answer = models.CharField(max_length=100)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-answered_at"]

    def __str__(self):
        return f"{self.patient_profile.user.username} - {self.question_type} - {self.is_correct}"
