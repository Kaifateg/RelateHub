from datetime import date, timedelta

from rest_framework import serializers

from gallery.serializers import PhotoSerializer
from matches.models import Swipe

from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    gender = serializers.CharField(source="get_gender_display")
    status = serializers.CharField(source="get_status_display")
    age = serializers.ReadOnlyField()
    main_photo_url = serializers.ReadOnlyField(source="main_photo")
    is_matched = serializers.SerializerMethodField()

    photos = PhotoSerializer(many=True, source="user.photos", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "first_name",
            "last_name",
            "middle_name",
            "gender",
            "birth_date",
            "age",
            "city",
            "bio",
            "status",
            "is_private",
            "likes_count",
            "main_photo_url",
            "is_matched",
            "photos",
        ]
        read_only_fields = [
            "user",
            "likes_count",
            "age",
            "main_photo_url",
            "is_matched",
            "photos",
        ]

    def get_is_matched(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            current_user = request.user
            target_user = obj.user
            return Swipe.check_match_exists(current_user, target_user)
        return False

    def to_representation(self, instance):
        """
        Динамически изменяет отображаемые поля в зависимости от настроек приватности.
        """
        ret = super().to_representation(instance)
        request = self.context.get("request")
        is_owner = (
            request and request.user.is_authenticated and request.user == instance.user
        )
        ret.pop("birth_date", None)

        if instance.is_private and not is_owner:
            ret["last_name"] = "Скрыто"
            ret.pop("birth_date", None)
        return ret

    def validate_birth_date(self, value):
        min_age_date = date.today() - timedelta(days=365 * 18 + 5)
        if value > min_age_date:
            raise serializers.ValidationError(
                "Пользователь должен быть " "старше 18 лет."
            )
        return value
