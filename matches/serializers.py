from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from profiles.serializers import ProfileSerializer
from users.models import CustomUser

from .models import ContactRequest, MatchAction, Swipe


class SwipeSerializer(serializers.ModelSerializer):
    swiped_user_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), source="swiped_user"
    )

    class Meta:
        model = Swipe
        fields = [
            "swiped_user_id",
            "is_like",
        ]

    def validate(self, data):
        """
        Проверяем, что пользователь не свайпает сам себя и что свайп уникален.
        """
        user = self.context["request"].user
        swiped_user = data.get("swiped_user")

        if user.id == swiped_user.id:
            raise serializers.ValidationError(
                {"error": "Вы не можете свайпнуть самого себя."}, code="invalid"
            )

        if Swipe.objects.filter(swiper=user, swiped_user=swiped_user).exists():
            raise serializers.ValidationError(
                {"error": "Вы уже свайпнули этого пользователя."}, code="unique"
            )

        return data


class MatchSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    email = serializers.ReadOnlyField()

    class Meta:
        model = get_user_model()
        fields = ["id", "email", "profile"]


class MatchActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchAction
        fields = ["id", "sender", "receiver", "sent_at"]
        read_only_fields = ["sender", "sent_at"]
        validators = [
            UniqueTogetherValidator(
                queryset=MatchAction.objects.all(),
                fields=["sender", "receiver"],
                message="Действие уже было совершено для этого мэтча.",
            )
        ]

    def create(self, validated_data):
        """Автоматически устанавливаем текущего пользователя как sender."""
        validated_data["sender"] = self.context["request"].user
        return super().create(validated_data)


class ContactRequestSerializer(serializers.ModelSerializer):
    sender_email = serializers.ReadOnlyField(source="sender.email")
    receiver_email = serializers.ReadOnlyField(source="receiver.email")

    class Meta:
        model = ContactRequest
        fields = [
            "id",
            "sender",
            "sender_email",
            "receiver",
            "receiver_email",
            "status",
            "sent_at",
            "responded_at",
            "sender_contact_email",
            "receiver_contact_email",
        ]
        read_only_fields = [
            "sender",
            "sent_at",
            "responded_at",
            "status",
            "sender_contact_email",
            "receiver_contact_email",
        ]
