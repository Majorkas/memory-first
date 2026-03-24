from datetime import date
from pathlib import Path

import cloudinary.uploader
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from user.models import SeedRunState

from user.models import CUser, CarerProfile, PatientCarerRelationship, PatientProfile


# Startup Command for ease of use to show off all features of the site

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


PATIENT_USER = {
    "username": "David.Williams",
    "password": "David.Williams",
    "first_name": "David",
    "last_name": "Williams",
    "email": "startup_patient@example.com",
    "user_type": CUser.User_type.PATIENT,
}
CARER_USER = {
    "username": "Noah.Parker",
    "password": "Noah.Parker",
    "first_name": "Noah",
    "last_name": "Parker",
    "email": "startup_carer@example.com",
    "user_type": CUser.User_type.CARER,
}

PATIENT_PROFILE_DEFAULTS = {
    "date_of_birth": date(1948, 5, 16),
    "address": "123 Memory Lane",
}
CARER_PROFILE_DEFAULTS = {
    "employer": "Memory First Care",
    "phone": "0868398657",
}

PATIENT_PHOTO = "seed_photos/startup/patient/profile.jpg"
CARER_PHOTO = "seed_photos/startup/carer/profile.jpg"

SEED_KEY = "startup_already_complete"

class Command(BaseCommand):
    help = "One-time startup seed: users, profiles, relationship, profile photos, then family/friends."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--skip-family-friends", action="store_true")

    def handle(self, *args, **options):
        force = options["force"]
        skip_family_friends = options["skip_family_friends"]

        already_ran = SeedRunState.objects.filter(key=SEED_KEY).exists()
        if already_ran and not force:
            self.stdout.write(self.style.WARNING("Already seeded. Use --force to run again."))
            return

        with transaction.atomic():
            patient = self._create_or_get_user(PATIENT_USER)
            carer = self._create_or_get_user(CARER_USER)

            patient_profile, _ = PatientProfile.objects.update_or_create(
                user=patient,
                defaults=PATIENT_PROFILE_DEFAULTS,
            )
            carer_profile, _ = CarerProfile.objects.update_or_create(
                user=carer,
                defaults=CARER_PROFILE_DEFAULTS,
            )

            PatientCarerRelationship.objects.update_or_create(
                patient=patient,
                carer=carer,
                defaults={"is_active": True},
            )

            self._attach_patient_photo(patient_profile, PATIENT_PHOTO)
            self._attach_carer_photo(carer_profile, CARER_PHOTO)

        if not skip_family_friends:
                call_command("seed_family_friends", patient_username=PATIENT_USER["username"])

        SeedRunState.objects.update_or_create(key=SEED_KEY, defaults={})

        self.stdout.write(self.style.SUCCESS("Startup seed complete."))

    def _create_or_get_user(self, data):
        user, created = CUser.objects.get_or_create(
            username=data["username"],
            defaults={
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "email": data["email"],
                "user_type": data["user_type"],
            },
        )

        changed = False
        for field in ("first_name", "last_name", "email", "user_type"):
            if getattr(user, field) != data[field]:
                setattr(user, field, data[field])
                changed = True

        if created:
            user.set_password(data["password"])
            changed = True

        if changed:
            user.save()

        return user

    def _attach_patient_photo(self, patient_profile, relative_path):
        photo_path = (Path(settings.BASE_DIR) / relative_path).resolve()
        if not photo_path.is_file() or photo_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        public_id = self._upload_image(photo_path, "patient_profile_pictures/")
        patient_profile.patient_profile_picture = public_id
        patient_profile.save(update_fields=["patient_profile_picture"])

    def _attach_carer_photo(self, carer_profile, relative_path):
        photo_path = (Path(settings.BASE_DIR) / relative_path).resolve()
        if not photo_path.is_file() or photo_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return
        public_id = self._upload_image(photo_path, "carer_profile_pictures/")
        carer_profile.carer_profile_picture = public_id
        carer_profile.save(update_fields=["carer_profile_picture"])

    def _upload_image(self, image_path: Path, cloud_folder: str) -> str:
        result = cloudinary.uploader.upload(
            str(image_path),
            folder=cloud_folder,
            transformation={
                "crop": "fill",
                "gravity": "face",
                "quality": "auto",
                "fetch_format": "auto",
            },
        )
        return result["public_id"]
