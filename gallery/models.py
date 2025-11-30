from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Photo(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("Пользователь"),
    )

    # Само изображение
    image = models.ImageField(
        upload_to="profile_photos/", verbose_name=_("Файл изображения")
    )

    is_main = models.BooleanField(default=False, verbose_name=_("Главная фотография"))

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Фотография профиля")
        verbose_name_plural = _("Фотографии профилей")
        ordering = ["-is_main", "-uploaded_at"]

    def __str__(self):
        return f"Фото {self.id} пользователя {self.user.email}"


@receiver(pre_save, sender=Photo)
def set_main_photo_unique(sender, instance, **kwargs):
    if instance.is_main:
        Photo.objects.filter(user=instance.user, is_main=True).exclude(
            pk=instance.pk
        ).update(is_main=False)
