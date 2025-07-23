from rest_framework import serializers
from .models import Note

# class NoteSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Note
#         fields = ['id', 'note']


class NoteSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Note
        fields = ['user', 'note', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']
