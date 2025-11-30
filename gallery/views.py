from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Photo
from .serializers import PhotoSerializer

# Create your views here.
PHOTO_UPLOAD_LIMIT = 10


class PhotoViewSet(viewsets.ModelViewSet):
    """
    API endpoint для управления фотографиями профиля аутентифицированного пользователя.
    """

    serializer_class = PhotoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Гарантирует, что пользователь может управлять только своими фотографиями.
        """
        return Photo.objects.filter(user=self.request.user).order_by("-uploaded_at")

    def perform_create(self, serializer):
        """
        Проверяет лимит фотографий перед сохранением и устанавливает владельца/главное фото.
        """
        user = self.request.user

        if self.get_queryset().count() >= PHOTO_UPLOAD_LIMIT:
            raise serializers.ValidationError(
                f"Вы достигли лимита в {PHOTO_UPLOAD_LIMIT} фотографий. Удалите старые фото, чтобы добавить новые."
            )
        # ------------------------

        photo_instance = serializer.save(user=user)

        if self.get_queryset().count() == 1:
            photo_instance.is_main = True
            photo_instance.save()
