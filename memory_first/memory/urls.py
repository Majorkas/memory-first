from django.urls import path
from .views import MemoryGamePageView, FamilyMemoryQuestionAPIView, FamilyMemorySubmitAPIView

urlpatterns = [
    path("game/", MemoryGamePageView.as_view(), name="memory_game_page"),
    path("api/family-memory/question/", FamilyMemoryQuestionAPIView.as_view(), name="family_memory_question"),
    path("api/family-memory/submit/", FamilyMemorySubmitAPIView.as_view(), name="family_memory_submit"),
]
