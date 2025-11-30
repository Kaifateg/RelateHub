from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import CustomUser


class UserAuthenticationTests(APITestCase):
    def setUp(self):
        self.register_url = reverse("user-list")
        self.login_url = reverse("jwt-create")

    def test_user_registration(self):
        """
        Проверяем, что новый пользователь может успешно зарегистрироваться.
        """
        data = {"email": "testuser@example.com", "password": "StrongP@ss123"}
        response = self.client.post(self.register_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(CustomUser.objects.get().email, "testuser@example.com")

    def test_user_login_and_jwt_token_acquisition(self):
        """
        Проверяем, что пользователь может войти в систему и получить JWT-токены.
        """
        CustomUser.objects.create_user(
            email="loginuser@example.com", password="StrongP@ss123"
        )

        data = {"email": "loginuser@example.com", "password": "StrongP@ss123"}
        response = self.client.post(self.login_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_registration_with_invalid_email(self):
        """
        Проверяем валидацию email при регистрации.
        """
        data = {"email": "invalid-email", "password": "password"}
        response = self.client.post(self.register_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
