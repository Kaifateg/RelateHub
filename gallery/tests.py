import os

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APITestCase

from .models import Photo
from .serializers import MAX_UPLOAD_SIZE, PhotoSerializer
from .views import PHOTO_UPLOAD_LIMIT

User = get_user_model()


class PhotoGalleryTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            email="user1@test.com", password="password123"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", password="password123"
        )
        self.list_url = reverse("photo-list")  # /api/photos/

        self.image_content_gif = b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\xff\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b"

        self.image_file = SimpleUploadedFile(
            name="test_image.gif",
            content=self.image_content_gif,
            content_type="image/gif",
        )

        large_content = self.image_content_gif * 10000

        self.image_file_large = SimpleUploadedFile(
            name="large_image.gif", content=large_content, content_type="image/gif"
        )

    def tearDown(self):
        for photo in Photo.objects.all():
            if os.path.exists(photo.image.path):
                os.remove(photo.image.path)

    # --- Тесты доступа и листинга ---

    def test_list_own_photos(self):
        """Пользователь видит только свои фотографии."""
        Photo.objects.create(user=self.user1, image=self.image_file, is_main=True)
        Photo.objects.create(user=self.user2, image=self.image_file)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["is_main"], True)

    def test_unauthenticated_access(self):
        """Неаутентифицированный пользователь не имеет доступа."""
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = self.client.post(self.list_url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Тесты создания и валидации ---

    def test_upload_photo(self):
        """Успешная загрузка фотографии."""
        self.client.force_authenticate(user=self.user1)
        data = {"image": self.image_file, "is_main": False}
        response = self.client.post(self.list_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Photo.objects.filter(user=self.user1).count(), 1)
        self.assertTrue(Photo.objects.get(user=self.user1).is_main)

    def test_upload_photo_limit(self):
        """Проверка ограничения на количество фотографий."""

        self.assertGreater(PHOTO_UPLOAD_LIMIT, 0)

        for i in range(PHOTO_UPLOAD_LIMIT):
            img_file = SimpleUploadedFile(
                name=f"img_{i}.gif",
                content=self.image_content_gif,
                content_type="image/gif",
            )
            Photo.objects.create(user=self.user1, image=img_file)

        self.client.force_authenticate(user=self.user1)

        extra_file = SimpleUploadedFile(
            name="extra.gif", content=self.image_content_gif, content_type="image/gif"
        )
        data = {"image": extra_file}
        response = self.client.post(self.list_url, data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Вы достигли лимита", str(response.data))

    def test_serializer_validate_image_size(self):
        """Тестирование валидатора размера напрямую."""
        serializer = PhotoSerializer()

        small_but_fake_large_file = SimpleUploadedFile(
            name="fake_large.gif", content=b"small", content_type="image/gif"
        )
        small_but_fake_large_file.size = MAX_UPLOAD_SIZE + 100

        with self.assertRaisesMessage(
            DRFValidationError, "Размер файла слишком большой"
        ):
            serializer.validate_image(small_but_fake_large_file)

    # --- Тесты обновления и удаления ---

    def test_update_photo_is_main(self):
        """Проверка логики is_main при обновлении."""
        photo1 = Photo.objects.create(
            user=self.user1, image=self.image_file, is_main=True
        )
        photo2 = Photo.objects.create(
            user=self.user1,
            image=SimpleUploadedFile("p2.jpg", b"c", content_type="image/jpeg"),
            is_main=False,
        )

        self.client.force_authenticate(user=self.user1)
        detail_url = reverse("photo-detail", kwargs={"pk": photo2.pk})
        response = self.client.patch(detail_url, {"is_main": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        photo2.refresh_from_db()
        self.assertTrue(photo2.is_main)

        photo1.refresh_from_db()
        self.assertFalse(photo1.is_main)

    def test_delete_own_photo(self):
        """Удаление своей фотографии."""
        photo1 = Photo.objects.create(
            user=self.user1, image=self.image_file, is_main=True
        )
        self.client.force_authenticate(user=self.user1)
        detail_url = reverse("photo-detail", kwargs={"pk": photo1.pk})

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Photo.objects.filter(user=self.user1).count(), 0)

    def test_delete_other_user_photo(self):
        """Попытка удаления чужой фотографии."""
        photo1 = Photo.objects.create(
            user=self.user1, image=self.image_file, is_main=True
        )

        self.client.force_authenticate(user=self.user2)
        detail_url = reverse("photo-detail", kwargs={"pk": photo1.pk})

        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Photo.objects.filter(user=self.user1).count(), 1)
