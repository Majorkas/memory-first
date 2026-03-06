from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from cloudinary.models import CloudinaryField


class CUser(AbstractUser):
    class User_type(models.TextChoices):
        CARER = "carer" , "Carer"
        PATIENT = "patient", "Patient"

    user_type = models.CharField(max_length=20,choices=User_type.choices, default=User_type.CARER)

    def __str__(self):
        return f'{self.username} is a {self.user_type}'

    def is_carer(self):
        """checks if the user is a Carer"""
        return self.user_type in ['carer']

    def is_patient(self):
        """checks if the user is a Patient"""
        return self.user_type in ['patient']

    def get_carers(self):
        """Get all active carers of a Patient"""
        return CUser.objects.filter(patient_link__patient=self, patient_link__is_active=True)

    def get_patients(self):
        """Get all active patients of a Carer"""
        if not self.is_carer():
            return CUser.objects.none()
        else:
            return CUser.objects.filter(carer_link__carer=self, carer_link__is_active=True)

class PatientProfile(models.Model):
    patient_profile_picture = CloudinaryField('image', blank=True, null=True, folder='patient_profile_pictures/', transformation={
            'width': 200,
            'height': 200,
            'crop': 'fill',
            'gravity': 'face',
            'quality': 'auto',
            'fetch_format': 'auto'
        } )
    user = models.OneToOneField(CUser,on_delete=models.CASCADE,related_name='patient_profile',limit_choices_to={"user_type": CUser.User_type.PATIENT},)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.CharField(max_length=255,null=True, blank=True)

    def clean(self):
        if self.user and not self.user.is_patient():
            raise ValidationError("PatientProfile.user must be a patient user.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"PatientProfile({self.user.username})"

class CarerProfile(models.Model):
    carer_profile_picture = CloudinaryField('image', blank=True, null=True, folder='carer_profile_pictures/', transformation={
            'width': 200,
            'height': 200,
            'crop': 'fill',
            'gravity': 'face',
            'quality': 'auto',
            'fetch_format': 'auto'
        } )
    user = models.OneToOneField(CUser,on_delete=models.CASCADE,related_name="carer_profile",limit_choices_to={"user_type": CUser.User_type.CARER},)
    employer = models.CharField(max_length=30, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)

    def clean(self):
        if self.user and not self.user.is_carer():
            raise ValidationError("CarerProfile.user must be a carer user.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"CarerProfile({self.user.username})"



class PatientCarerRelationship(models.Model):
    patient = models.ForeignKey(CUser, on_delete=models.CASCADE, related_name='carer_link')
    carer = models.ForeignKey(CUser, on_delete=models.CASCADE, related_name='patient_link', limit_choices_to={'user_type__in' : ['carer']})
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('patient', 'carer')

    def clean(self):
        if not self.carer.is_carer():
            raise ValidationError(f'{self.carer.username} is not a Carer')
        if not self.patient.is_patient():
            raise ValidationError(f'{self.patient.username} is not a Patient')
        if self.patient == self.carer:
            raise ValidationError(f'A Patient cannot care for themselves')
    def save(self,*args,**kwargs):
        self.clean()
        super().save(*args,**kwargs)

    def __str__(self):
        return f'{self.carer.username} cares for {self.patient.username}'


class FamilyFriend(models.Model):
    image = CloudinaryField('image', blank=True, null=True, folder='family_friend_pictures/', transformation={
            'crop': 'fill',
            'gravity': 'face',
            'quality': 'auto',
            'fetch_format': 'auto'
        } )
    name = models.CharField(max_length=30)
    relationship = models.CharField(max_length=20, blank=True)
    patient_profile = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='family_friend')
    emergency_contact = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.relationship}) for {self.patient_profile.user.username}"
