from rest_framework import serializers

from .models import CustomUser


class CustomUserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ("email", "password")
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        return user


class CustomUserSerializer(serializers.ModelSerializer):

    profile_id = serializers.IntegerField(source="profile.id", read_only=True)

    class Meta:
        model = CustomUser
        fields = ["id", "email", "is_active", "date_joined", "profile_id"]
        read_only_fields = ["email", "date_joined", "is_active"]
