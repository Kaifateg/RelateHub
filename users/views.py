from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CustomUser
from .serializers import CustomUserCreateSerializer, CustomUserSerializer


# Create your views here.
class CustomUserViewSet(viewsets.ModelViewSet):
    """
    API endpoint, который позволяет просматривать пользователей.
    Мы используем ReadOnlyModelViewSet, чтобы предотвратить создание/удаление
    пользователей через этот ViewSet напрямую (регистрация будет отдельным процессом).
    """

    queryset = CustomUser.objects.all().order_by("-date_joined")
    serializer_class = CustomUserSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        """
        Выбирает сериализатор в зависимости от действия.
        """
        if self.action == "create":
            return CustomUserCreateSerializer
        return CustomUserSerializer

    def get_permissions(self):
        """
        Выбирает права доступа в зависимости от действия.
        """
        if self.action == "create":
            self.permission_classes = [AllowAny]

        else:
            self.permission_classes = [IsAuthenticated]

        return [permission() for permission in self.permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )
