from django.contrib import admin
from .models import CUser, CarerProfile, PatientCarerRelationship, PatientProfile, FamilyFriend


admin.site.register(CUser)
admin.site.register(CarerProfile)
admin.site.register(PatientCarerRelationship)
admin.site.register(PatientProfile)
admin.site.register(FamilyFriend)
