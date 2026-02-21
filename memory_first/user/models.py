from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class User_type(models.TextChoices):
        CARER = "carer" , "Carer"
        PATIENT = "patient", "Patient"

    user_type = models.CharField(max_length=20,choices=User_type.choices, default=User_type.CARER)
