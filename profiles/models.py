from django.conf import settings
from django.db import models
from django.utils import timezone

# Create your models here.
STATUS_CHOICES = (
    ("search", "В поиске"),
    ("busy", "Занят(а)"),
    ("married", "В браке"),
    ("complicated", "Все сложно"),
)
GENDER_CHOICES = (
    ("M", "Мужской"),
    ("F", "Женский"),
    ("O", "Другой/Не указан"),
)


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )

    first_name = models.CharField(max_length=100, blank=False)
    last_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="Отчество"
    )
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=False, verbose_name="Пол"
    )

    birth_date = models.DateField(null=False, blank=False, verbose_name="Дата рождения")

    city = models.CharField(max_length=100, blank=False)

    bio = models.TextField(
        max_length=500, blank=True, verbose_name="О себе и увлечения"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="search",
        blank=False,
    )

    is_private = models.BooleanField(default=False, verbose_name="Приватный профиль")

    likes_count = models.PositiveIntegerField(default=0)

    @property
    def main_photo(self):
        main = self.user.photos.filter(is_main=True).first()
        if main:
            return main.image.url
        fallback = self.user.photos.first()
        if fallback:
            return fallback.image.url
        return None

    def __str__(self):
        return f"Профиль пользователя {self.user.email}"

    @property
    def age(self):
        if self.birth_date:
            today = timezone.now().date()
            return (
                today.year
                - self.birth_date.year
                - (
                    (today.month, today.day)
                    < (self.birth_date.month, self.birth_date.day)
                )
            )
        return None
