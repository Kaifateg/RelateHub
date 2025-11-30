import datetime

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from profiles.models import Profile
from users.models import CustomUser


class ProfileTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="test@example.com", password="password123"
        )

        self.profile = Profile.objects.create(
            user=self.user,
            first_name="Test",
            birth_date=datetime.date(1990, 1, 1),
            gender="M",
            city="Test City",
        )
        self.profile_url = reverse("profile-me")

        self.client.force_authenticate(user=self.user)

    def test_retrieve_own_profile(self):
        """
        Проверяем, что пользователь может получить данные своего профиля.
        """
        response = self.client.get(self.profile_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Test")
        self.assertIn("is_matched", response.data)

    def test_update_profile_city(self):
        """
        Проверяем, что пользователь может обновить свой город.
        """
        data = {"city": "New City Name"}
        response = self.client.patch(self.profile_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.city, "New City Name")
        self.assertEqual(response.data["city"], "New City Name")

    def test_age_validation(self):
        """
        Проверяем, что нельзя установить возраст младше 18 лет.
        """
        today = datetime.date.today()
        recent_birth_date = today.replace(year=today.year - 5)

        data = {"birth_date": recent_birth_date.strftime("%Y-%m-%d")}
        response = self.client.patch(self.profile_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn(
            "Пользователь должен быть старше 18 лет", response.data["birth_date"][0]
        )

        self.assertNotIn("non_field_errors", response.data)
