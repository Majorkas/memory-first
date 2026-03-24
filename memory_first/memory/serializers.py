from rest_framework import serializers


class FamilyMemorySubmitSerializer(serializers.Serializer):
    answer = serializers.CharField(allow_blank=True, required=False, default="")
