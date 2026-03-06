from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from .models import CUser, PatientProfile, CarerProfile


@receiver(post_save, sender=CUser)
def ensure_correct_profile(sender, instance: CUser, **kwargs):

    if instance.is_patient():
        PatientProfile.objects.get_or_create(user=instance)
    elif instance.is_carer():
        CarerProfile.objects.get_or_create(user=instance)
    else:
        raise ValidationError("Invalid user_type.")
