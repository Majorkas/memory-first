import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = """Creates an admin user non-interactively if it doesn't exist

    Provide the following required environment variables:
    DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD
    """

    def handle(self, *_args, **_kwargs):
        User = get_user_model()

        username = os.environ["DJANGO_SUPERUSER_USERNAME"]
        email = os.environ["DJANGO_SUPERUSER_EMAIL"]
        password = os.environ["DJANGO_SUPERUSER_PASSWORD"]

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"The superuser '{username}' was created successfully"))
