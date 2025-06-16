from rest_framework import serializers
from .models import PayworldData

class PayworldDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayworldData
        fields = '__all__'