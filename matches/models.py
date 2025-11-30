from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import (Count, ExpressionWrapper, F, OuterRef, Subquery,
                              fields)
from django.db.models.functions import ExtractYear
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# Create your models here.
class SwipeManager(models.Manager):
    def for_user(self, user):
        """Возвращает QuerySet свайпов, сделанных данным пользователем."""
        return self.filter(swiper=user)

    def liked_by(self, user):
        """Возвращает QuerySet пользователей, которых лайкнул данный пользователь."""
        return (
            self.for_user(user)
            .filter(is_like=True)
            .values_list("swiped_user", flat=True)
        )

    def disliked_by(self, user):
        """Возвращает QuerySet пользователей, которых дизлайкнул данный пользователь."""
        return (
            self.for_user(user)
            .filter(is_like=False)
            .values_list("swiped_user", flat=True)
        )

    def received_likes(self, user):
        """Возвращает QuerySet пользователей, которые лайкнули данного пользователя."""
        return self.filter(swiped_user=user, is_like=True).values_list(
            "swiper", flat=True
        )

    def get_matches(self, user):
        """
        Возвращает QuerySet пользователей, с которыми есть взаимная симпатия (Match),
        оптимизированный в один запрос с помощью подзапросов.
        """
        User = get_user_model()

        user_likes_them = (
            Swipe.objects.filter(swiper=user, swiped_user=OuterRef("pk"), is_like=True)
            .values("swiped_user_id")
            .annotate(count=Count("swiped_user_id"))
            .values("count")
        )

        they_like_user = (
            Swipe.objects.filter(swiper=OuterRef("pk"), swiped_user=user, is_like=True)
            .values("swiper_id")
            .annotate(count=Count("swiper_id"))
            .values("count")
        )

        queryset = (
            User.objects.exclude(id=user.id)
            .annotate(
                liked_by_user=Subquery(
                    user_likes_them, output_field=fields.IntegerField()
                ),
                likes_user=Subquery(they_like_user, output_field=fields.IntegerField()),
            )
            .filter(liked_by_user__gte=1, likes_user__gte=1)
        )

        queryset = queryset.select_related("profile")
        return queryset


class Swipe(models.Model):
    swiper = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_swipes",
        verbose_name=_("Кто свайпнул"),
    )
    swiped_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_swipes",
        verbose_name=_("Кого свайпнули"),
    )
    is_like = models.BooleanField(verbose_name=_("Лайк?"))
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = SwipeManager()

    class Meta:
        verbose_name = _("Свайп")
        verbose_name_plural = _("Свайпы")
        unique_together = ("swiper", "swiped_user")

    def __str__(self):
        action = "Лайк" if self.is_like else "Дизлайк"
        return f"{self.swiper.email} поставил {action} пользователю {self.swiped_user.email}"

    @staticmethod
    def get_viewable_profiles_queryset(user, filters=None):
        """
        Возвращает QuerySet ВСЕХ профилей, доступных для просмотра (еще не
        свайпнутых и не сам пользователь), с применением фильтров.
        """
        excluded_users = [user.id]
        already_swiped_ids = Swipe.objects.for_user(user).values_list(
            "swiped_user_id", flat=True
        )
        excluded_users.extend(already_swiped_ids)

        profiles_qs = settings.AUTH_USER_MODEL.objects.exclude(id__in=excluded_users)
        profiles_qs = profiles_qs.exclude(is_staff=True).filter(is_active=True)

        if filters:
            if "gender" in filters:
                profiles_qs = profiles_qs.filter(profile__gender=filters["gender"])
            if "city" in filters:
                profiles_qs = profiles_qs.filter(
                    profile__city__icontains=filters["city"]
                )
            if "status" in filters:
                profiles_qs = profiles_qs.filter(profile__status=filters["status"])

            if "min_age" in filters or "max_age" in filters:
                age_sql = ExpressionWrapper(
                    ExtractYear(date.today()) - ExtractYear(F("profile__birth_date")),
                    output_field=fields.IntegerField(),
                )
                profiles_qs = profiles_qs.annotate(age=age_sql)

                if "min_age" in filters:
                    profiles_qs = profiles_qs.filter(age__gte=filters["min_age"])
                if "max_age" in filters:
                    profiles_qs = profiles_qs.filter(age__lte=filters["max_age"])

        return profiles_qs.order_by("-date_joined")

    @staticmethod
    def check_match_exists(user1, user2):
        """
        Проверяет, существует ли взаимный лайк (мэтч) между user1 и user2.
        """
        liked_1_to_2 = Swipe.objects.filter(
            swiper=user1, swiped_user=user2, is_like=True
        ).exists()

        liked_2_to_1 = Swipe.objects.filter(
            swiper=user2, swiped_user=user1, is_like=True
        ).exists()

        return liked_1_to_2 and liked_2_to_1


class MatchAction(models.Model):
    """
    Модель отслеживает факт приглашения/обмена контактами между двумя
    пользователями, у которых уже есть мэтч.
    """

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_match_actions",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_match_actions",
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Действие мэтча (Приглашение/Контакт)")
        verbose_name_plural = _("Действия мэтчей")
        unique_together = ("sender", "receiver")


REQUEST_STATUS_CHOICES = (
    ("sent", "Отправлен"),
    ("accepted", "Принят"),
    ("declined", "Отклонен"),
)


class ContactRequest(models.Model):
    """
    Модель для управления запросами на обмен контактами/приглашениями после мэтча.
    """

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_contact_requests",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_contact_requests",
    )
    status = models.CharField(
        max_length=10, choices=REQUEST_STATUS_CHOICES, default="sent"
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    sender_contact_email = models.EmailField(null=True, blank=True)
    receiver_contact_email = models.EmailField(null=True, blank=True)

    class Meta:
        verbose_name = _("Запрос на контакт")
        verbose_name_plural = _("Запросы на контакты")
        unique_together = ("sender", "receiver")
        ordering = ["-sent_at"]

    def __str__(self):
        return f"Запрос от {self.sender.email} к {self.receiver.email} ({self.status})"

    def accept(self):
        """Обрабатывает принятие запроса на контакт, обменивается email и сохраняет."""
        if self.status != "sent":
            return False, "Запрос уже был обработан."

        self.status = "accepted"
        self.responded_at = timezone.now()
        self.sender_contact_email = self.sender.email
        self.receiver_contact_email = self.receiver.email
        self.save()
        return True, "Запрос успешно принят."

    def decline(self):
        """Обрабатывает отклонение запроса на контакт и сохраняет."""
        if self.status != "sent":
            return False, "Запрос уже был обработан."

        self.status = "declined"
        self.responded_at = timezone.now()
        self.save()
        return True, "Запрос успешно отклонен."
