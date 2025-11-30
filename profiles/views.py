from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Profile
from .serializers import ProfileSerializer


# Create your views here.
class ProfileViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint, который позволяет просматривать или редактировать
    собственный профиль аутентифицированного пользователя.
    """

    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]  # Требуем аутентификацию

    def get_queryset(self):
        """
        Гарантирует, что пользователь может видеть/редактировать только свой профиль.
        """
        return Profile.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get", "put", "patch"])
    def me(self, request, *args, **kwargs):
        profile = self.get_queryset().first()
        if not profile:
            return Response(
                {"detail": "Профиль не найден."}, status=status.HTTP_404_NOT_FOUND
            )

        if request.method == "GET":
            serializer = self.get_serializer(profile)
            return Response(serializer.data)

        elif request.method in ("PUT", "PATCH"):
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
