from django.template.defaultfilters import filesizeformat
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Photo

MAX_UPLOAD_SIZE = 5242880
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/gif"]


class PhotoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Photo
        fields = [
            "id",
            "image",
            "is_main",
        ]

    @staticmethod
    def validate_image(value):
        """
        Валидация размера файла и типа контента.
        """
        if value.size > MAX_UPLOAD_SIZE:
            raise ValidationError(
                f"Размер файла слишком большой. Максимальный размер: {filesizeformat(MAX_UPLOAD_SIZE)}."
            )

        if value.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError(
                f"Поддерживаются только форматы: {', '.join(ALLOWED_CONTENT_TYPES)}."
            )
        return value
