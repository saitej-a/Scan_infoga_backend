from rest_framework import serializers
from .models import HudsonRockData, SearchByEmail, SearchByIP

class HudsonRockDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = HudsonRockData
        fields = '__all__'

    def validate_data_type(self, value):
        valid_types = ['email', 'domain']  # Add other valid types
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid data type. Must be one of {valid_types}")
        return value

class SearchByEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchByEmail
        fields = '__all__'

class SearchByIPSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchByIP
        fields = '__all__'