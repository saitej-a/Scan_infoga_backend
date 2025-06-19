from rest_framework import serializers
from .models import PayworldData, RazorpayIFSCData

class PayworldDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayworldData
        fields = ['sender_mobile_number', 'result', 'created_at', 'updated_at']

class RazorpayIFSCDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = RazorpayIFSCData
        fields = ['ifsc_code', 'result', 'created_at', 'updated_at']
