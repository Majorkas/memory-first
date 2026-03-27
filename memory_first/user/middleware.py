import logging
from datetime import timedelta, datetime

from django.contrib import messages
from django.urls import reverse
from django.utils import timezone

from memory.models import MemoryGameAttempt

logger = logging.getLogger(__name__)


class MemoryGameReminderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        excluded_prefixes = (
            "/accounts/",
            "/admin/",
        )

        if request.path.startswith(excluded_prefixes):
            return self.get_response(request)

        if request.user.is_authenticated and request.user.is_patient():
            excluded_paths = {
                reverse("memory_game_page"),
                reverse("family_memory_question"),
                reverse("family_memory_submit"),
                reverse("memory_reminder_snooze"),
            }

            if request.path not in excluded_paths:
                try:
                    patient_profile = request.user.patient_profile
                    cutoff = timezone.now() - timedelta(hours=24)

                    has_recent_attempt = MemoryGameAttempt.objects.filter(
                        patient_profile=patient_profile,
                        answered_at__gte=cutoff,
                    ).exists()

                    if has_recent_attempt:
                        request.session.pop("memory_reminder_added", None)
                        request.session.pop("memory_reminder_snooze_until", None)
                    else:
                        snooze_until_raw = request.session.get("memory_reminder_snooze_until")
                        snoozed = False

                        if snooze_until_raw:
                            snooze_until = datetime.fromisoformat(snooze_until_raw)
                            if timezone.is_naive(snooze_until):
                                snooze_until = timezone.make_aware(
                                    snooze_until,
                                    timezone.get_current_timezone(),
                                )
                            snoozed = timezone.now() < snooze_until

                        if not snoozed:
                            messages.info(
                                request,
                                "Don't forget to play the Memory Game today!",
                                extra_tags="memory_reminder",
                                fail_silently=True,
                            )

                except Exception:
                    logger.exception(
                        "MemoryGameReminderMiddleware failed for path=%s user_id=%s",
                        request.path,
                        getattr(request.user, "pk", None),
                    )

        return self.get_response(request)
