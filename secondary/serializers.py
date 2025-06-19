from rest_framework import serializers
from .models import PayworldData, RazorpayIFSCData, PayworldData2

class PayworldDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayworldData
        fields = ['sender_mobile_number', 'result', 'created_at', 'updated_at']
        
class PayworldData2Serializer(serializers.ModelSerializer):
    class Meta:
        model = PayworldData2
        fields = ['sender_mobile_number', 'result', 'created_at', 'updated_at']

class RazorpayIFSCDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = RazorpayIFSCData
        fields = ['ifsc_code', 'result', 'created_at', 'updated_at']
