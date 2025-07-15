from rest_framework import serializers
from decimal import Decimal

class DynamoDBItemSerializer(serializers.Serializer):
    class Meta:
        extra_kwargs = {'mobile_number': {'required': True}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in instance.items():
            if isinstance(value, type('')):
                data[key] = value
            elif isinstance(value, (int, float)):
                data[key] = value
            elif isinstance(value, list):
                data[key] = value
            elif isinstance(value, dict):
                data[key] = value
            elif isinstance(value, Decimal):
                if value % 1 == 0:
                    data[key] = int(value)
                else:
                    data[key] = float(value)
            else:
                data[key] = str(value)
        return data

class DynamoDBOLXItemSerializer:
    """Simple serializer without DRF serializers"""
    @staticmethod
    def serialize(items):
        result = []
        for item in items:
            clean_item = {}
            for key, value in item.items():
                if isinstance(value, Decimal):
                    if value % 1 == 0:
                        clean_item[key] = int(value)
                    else:
                        clean_item[key] = float(value)
                else:
                    clean_item[key] = value
            result.append(clean_item)
        return result