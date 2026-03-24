from pathlib import Path

import cloudinary.uploader
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from user.models import CUser, FamilyFriend, PatientProfile

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

FAMILY_FRIENDS = [
    {"name": "Emma Parker", "relationship": "Daughter", "filename": "emma.jpg", "emergency_contact": True},
    {"name": "Liam Parker", "relationship": "Son", "filename": "liam.jpg", "emergency_contact": False},
    {"name": "Maya Chen", "relationship": "Friend", "filename": "maya.jpg", "emergency_contact": False},
    {"name": "Olivia Brooks", "relationship": "Sister", "filename": "olivia.jpg", "emergency_contact": False},
    {"name": "Ethan Brooks", "relationship": "Brother", "filename": "ethan.jpg", "emergency_contact": False},
    {"name": "Sophia Reed", "relationship": "Niece", "filename": "sophia.jpg", "emergency_contact": False},
    {"name": "Jackson Reed", "relationship": "Nephew", "filename": "jackson.jpg", "emergency_contact": False},
    {"name": "Ava Patel", "relationship": "Friend", "filename": "ava.jpg", "emergency_contact": False},
    {"name": "Mason Patel", "relationship": "Friend", "filename": "mason.jpg", "emergency_contact": False},
    {"name": "Grace Turner", "relationship": "Neighbour", "filename": "grace.jpg", "emergency_contact": False},
    {"name": "Noah Bennett", "relationship": "Cousin", "filename": "noah.jpg", "emergency_contact": False},
    {"name": "Lucas Hayes", "relationship": "Friend", "filename": "lucas.jpg", "emergency_contact": False},
    {"name": "Benjamin Cole", "relationship": "Brother-in-law", "filename": "benjamin.jpg", "emergency_contact": False},
    {"name": "Henry Walsh", "relationship": "Neighbour", "filename": "henry.jpg", "emergency_contact": False},
]


class Command(BaseCommand):
    help = "Seed FamilyFriend records for a patient from a project-local folder."

    def add_arguments(self, parser):
        parser.add_argument("--patient-username", default="startup_patient", type=str)
        parser.add_argument("--photos-dir", default="seed_photos/startup/family_friends", type=str)

    def handle(self, *args, **options):
        patient_username = options["patient_username"]
        folder = (Path(settings.BASE_DIR) / options["photos_dir"]).resolve()

        try:
            patient_user = CUser.objects.get(username=patient_username, user_type=CUser.User_type.PATIENT)
        except CUser.DoesNotExist:
            raise CommandError(f"Patient user '{patient_username}' not found.")

        patient_profile, _ = PatientProfile.objects.get_or_create(user=patient_user)

        if not folder.is_dir():
            raise CommandError(f"Folder not found: {folder}")

        created = 0
        for item in FAMILY_FRIENDS:
            name = item["name"]
            image_path = folder / item["filename"]

            if not image_path.is_file():
                self.stdout.write(self.style.WARNING(f"Missing file: {image_path}"))
                continue
            if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                self.stdout.write(self.style.WARNING(f"Unsupported file: {image_path.name}"))
                continue
            if FamilyFriend.objects.filter(patient_profile=patient_profile, name=name).exists():
                self.stdout.write(self.style.WARNING(f"Skipping existing: {name}"))
                continue

            public_id = self._upload_image(image_path, "family_friend_pictures/")
            FamilyFriend.objects.create(
                patient_profile=patient_profile,
                name=name,
                relationship=item.get("relationship", ""),
                emergency_contact=item.get("emergency_contact", False),
                image=public_id,
            )
            created += 1
            self.stdout.write(self.style.SUCCESS(f"Created FamilyFriend: {name}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} FamilyFriend record(s)."))

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
