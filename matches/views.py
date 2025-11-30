from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from profiles.serializers import ProfileSerializer

from .models import ContactRequest, Swipe
from .serializers import (ContactRequestSerializer, MatchSerializer,
                          SwipeSerializer)

# Create your views here.
User = get_user_model()


class SwipeViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    API endpoint для создания свайпов (лайков/дизлайков).
    Пользователи могут только отправлять POST-запросы.
    """

    queryset = Swipe.objects.all()
    serializer_class = SwipeSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        swipe_instance = serializer.save(swiper=self.request.user)

        target_user_profile = swipe_instance.swiped_user.profile

        if swipe_instance.is_like:
            target_user_profile.likes_count += 1

        target_user_profile.save()


class MatchListViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """DRF вызовет этот метод автоматически для ListModelMixin."""
        user = self.request.user
        return Swipe.objects.get_matches(user)

    @action(detail=False, methods=["get"])
    def history(self, request):
        swiped_ids = Swipe.objects.for_user(request.user).values_list(
            "swiped_user_id", flat=True
        )
        history_users = User.objects.filter(id__in=swiped_ids)
        serializer = MatchSerializer(history_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def liked(self, request):
        liked_ids = Swipe.objects.liked_by(request.user)
        liked_users = User.objects.filter(id__in=liked_ids)
        serializer = MatchSerializer(liked_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def disliked(self, request):
        disliked_ids = Swipe.objects.disliked_by(request.user)
        disliked_users = User.objects.filter(id__in=disliked_ids)
        serializer = MatchSerializer(disliked_users, many=True)
        return Response(serializer.data)


class MatchListAPIView(views.APIView):
    """
    API endpoint для просмотра списка мэтчей (взаимных лайков).
    Используем APIView для полного контроля над ответом.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        queryset = Swipe.objects.get_matches(user)
        print(f"DEBUG VIEWS: get_matches returned Qty: {queryset.count()}")
        print(
            f"DEBUG VIEWS: User IDs returned: {list(queryset.values_list('id', flat=True))}"
        )

        serializer = MatchSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


class DiscoverListAPIView(generics.ListAPIView):
    """
    API endpoint для получения списка доступных профилей с фильтрацией и пагинацией.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_queryset(self):

        filters = {
            "gender": self.request.query_params.get("gender"),
            "city": self.request.query_params.get("city"),
            "status": self.request.query_params.get("status"),
            "min_age": self.request.query_params.get("min_age"),
            "max_age": self.request.query_params.get("max_age"),
        }

        clean_filters = {}
        for k, v in filters.items():
            if v is not None and v != "":
                if "age" in k:
                    try:
                        clean_filters[k] = int(v)
                    except ValueError:
                        raise ValidationError(
                            detail=f"Неверный формат возраста для параметра "
                            f"'{k}'. Ожидается целое число."
                        )
                else:
                    clean_filters[k] = v


class ContactRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoint для управления запросами на контакт.
    Пользователи видят только свои отправленные и полученные запросы.
    """

    serializer_class = ContactRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContactRequest.objects.filter(
            Q(sender=self.request.user) | Q(receiver=self.request.user)
        )

    def create(self, request, *args, **kwargs):
        """
        Переопределяем метод create, чтобы добавить логику проверки мэтча
        и уникальности запроса перед сохранением.
        """
        sender = request.user

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receiver_user = serializer.validated_data.get("receiver")

        if sender == receiver_user:
            return Response(
                {"error": "Вы не можете отправить запрос на контакт " "самому себе."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not Swipe.check_match_exists(sender, receiver_user):
            return Response(
                {
                    "error": "Вы не можете отправить запрос на контакт, "
                    "пока у вас нет взаимного лайка."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            ContactRequest.objects.filter(
                Q(sender=sender, receiver=receiver_user)
                | Q(sender=receiver_user, receiver=sender)
            )
            .exclude(status="declined")
            .exists()
        ):
            return Response(
                {
                    "error": "Запрос между вами и этим пользователем уже "
                    "существует или находится в обработке."
                },
                status=status.HTTP_409_CONFLICT,
            )

        instance = serializer.save(sender=sender)

        headers = self.get_success_headers(serializer.data)

        return Response(
            ContactRequestSerializer(instance).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @action(detail=True, methods=["patch"])
    def accept(self, request, pk=None):
        req = self.get_object()

        if req.receiver != request.user:
            return Response(
                {"error": "Вы не можете принять чужой запрос."},
                status=status.HTTP_403_FORBIDDEN,
            )

        success, message = req.accept()

        if not success:
            return Response({"error": message}, status=status.HTTP_409_CONFLICT)

        serializer = self.get_serializer(req)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def decline(self, request, pk=None):
        req = self.get_object()

        if req.receiver != request.user:
            return Response(
                {"error": "Вы не можете отклонить чужой запрос."},
                status=status.HTTP_403_FORBIDDEN,
            )

        success, message = req.decline()

        if not success:
            return Response({"error": message}, status=status.HTTP_409_CONFLICT)

        serializer = self.get_serializer(req)
        return Response(serializer.data)
