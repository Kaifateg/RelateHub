from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from profiles.models import Profile  # Убедитесь, что импорт корректен

from .models import ContactRequest, Swipe

User = get_user_model()


class SwipeTestCase(APITestCase):
    def setUp(self):
        self.swipe_url = reverse("swipe-list")
        self.user1 = User.objects.create_user(
            email="user1@test.com", password="password123"
        )
        self.user2 = User.objects.create_user(
            email="user2@test.com", password="password123"
        )
        self.user3 = User.objects.create_user(
            email="user3@test.com", password="password123"
        )

        Profile.objects.create(
            user=self.user1,
            birth_date=date.today() - timedelta(days=25 * 365),
            gender="M",
        )
        Profile.objects.create(
            user=self.user2,
            birth_date=date.today() - timedelta(days=25 * 365),
            gender="F",
        )
        Profile.objects.create(
            user=self.user3,
            birth_date=date.today() - timedelta(days=30 * 365),
            gender="F",
        )

        self.matches_url = reverse("match-list")

    def test_create_swipe_like(self):
        """Тест создания успешного лайка."""
        self.client.force_authenticate(user=self.user1)
        data = {"swiped_user_id": self.user2.id, "is_like": True}
        response = self.client.post(self.swipe_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Swipe.objects.filter(
                swiper=self.user1, swiped_user=self.user2, is_like=True
            ).exists()
        )
        self.user2.profile.refresh_from_db()

    def test_create_swipe_dislike(self):
        """Тест создания успешного дизлайка."""
        self.client.force_authenticate(user=self.user1)
        data = {"swiped_user_id": self.user3.id, "is_like": False}
        response = self.client.post(self.swipe_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Swipe.objects.filter(
                swiper=self.user1, swiped_user=self.user3, is_like=False
            ).exists()
        )

    def test_swipe_self(self):
        """Тест попытки свайпнуть самого себя."""
        self.client.force_authenticate(user=self.user1)
        data = {"swiped_user_id": self.user1.id, "is_like": True}
        response = self.client.post(self.swipe_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.data.get("error", [])

        found = any("Вы не можете свайпнуть самого себя" in str(e) for e in errors)
        self.assertTrue(found, f"Ожидаемая ошибка не найдена в ответах: {errors}")

    def test_swipe_duplicate(self):
        """Тест попытки повторного свайпа."""
        Swipe.objects.create(swiper=self.user1, swiped_user=self.user2, is_like=True)
        self.client.force_authenticate(user=self.user1)
        data = {"swiped_user_id": self.user2.id, "is_like": False}
        response = self.client.post(self.swipe_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        errors = response.data.get("error", [])
        found = any("Вы уже свайпнули этого пользователя" in str(e) for e in errors)
        self.assertTrue(found, f"Ожидаемая ошибка не найдена в ответах: {errors}")


class MatchTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="u1@test.com", password="p1")
        self.user2 = User.objects.create_user(email="u2@test.com", password="p2")
        self.user3 = User.objects.create_user(email="u3@test.com", password="p3")

        Profile.objects.create(
            user=self.user1,
            birth_date=date.today() - timedelta(days=25 * 365),
            gender="M",
        )
        Profile.objects.create(
            user=self.user2,
            birth_date=date.today() - timedelta(days=25 * 365),
            gender="F",
        )
        Profile.objects.create(
            user=self.user3,
            birth_date=date.today() - timedelta(days=30 * 365),
            gender="F",
        )

        self.matches_url = reverse("match-list")

    def test_no_matches(self):
        """Тест получения пустого списка мэтчей без взаимных лайков."""
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.matches_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    def test_single_match(self):
        """Тест получения мэтча при взаимном лайке."""

        Swipe.objects.create(swiper=self.user1, swiped_user=self.user2, is_like=True)

        Swipe.objects.create(swiper=self.user2, swiped_user=self.user1, is_like=True)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.matches_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["email"], self.user2.email)

    def test_liked_history(self):
        """Тест эндпоинта /api/matches/liked/"""
        Swipe.objects.create(swiper=self.user1, swiped_user=self.user2, is_like=True)
        Swipe.objects.create(swiper=self.user1, swiped_user=self.user3, is_like=False)

        url = reverse("match-liked")
        self.client.force_authenticate(user=self.user1)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], self.user2.email)


class ContactRequestTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="u1@test.com", password="p1")
        self.user2 = User.objects.create_user(email="u2@test.com", password="p2")
        self.user3 = User.objects.create_user(email="u3@test.com", password="p3")

        Profile.objects.create(
            user=self.user1,
            birth_date=date.today() - timedelta(days=25 * 365),
            gender="M",
        )
        Profile.objects.create(
            user=self.user2,
            birth_date=date.today() - timedelta(days=25 * 365),
            gender="F",
        )
        Profile.objects.create(
            user=self.user3,
            birth_date=date.today() - timedelta(days=30 * 365),
            gender="F",
        )

        self.request_url = reverse("contact-request-list")

    def establish_match(self, u1, u2):
        """Вспомогательная функция для создания мэтча."""
        Swipe.objects.create(swiper=u1, swiped_user=u2, is_like=True)
        Swipe.objects.create(swiper=u2, swiped_user=u1, is_like=True)

    def test_create_request_no_match(self):
        """Нельзя отправить запрос без мэтча."""
        self.client.force_authenticate(user=self.user1)
        data = {"receiver": self.user2.id}
        response = self.client.post(self.request_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("пока у вас нет взаимного лайка", response.data["error"])

    def test_create_request_success(self):
        """Успешное создание запроса при наличии мэтча."""
        self.establish_match(self.user1, self.user2)
        self.client.force_authenticate(user=self.user1)
        data = {"receiver": self.user2.id}
        response = self.client.post(self.request_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "sent")
        self.assertTrue(
            ContactRequest.objects.filter(
                sender=self.user1, receiver=self.user2
            ).exists()
        )

    def test_accept_request(self):
        """Тест принятия запроса."""
        self.establish_match(self.user1, self.user2)
        req = ContactRequest.objects.create(
            sender=self.user1, receiver=self.user2, status="sent"
        )

        # User 2 принимает запрос от User 1
        self.client.force_authenticate(user=self.user2)
        accept_url = reverse(
            "contact-request-accept", kwargs={"pk": req.pk}
        )  # URL: /api/contact-requests/{id}/accept/
        response = self.client.patch(accept_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "accepted")
        self.assertEqual(response.data["sender_contact_email"], self.user1.email)
        self.assertEqual(response.data["receiver_contact_email"], self.user2.email)

        req.refresh_from_db()
        self.assertEqual(req.status, "accepted")

    def test_decline_request(self):
        """Тест отклонения запроса."""
        self.establish_match(self.user1, self.user2)
        req = ContactRequest.objects.create(
            sender=self.user1, receiver=self.user2, status="sent"
        )

        # User 2 отклоняет запрос от User 1
        self.client.force_authenticate(user=self.user2)
        decline_url = reverse(
            "contact-request-decline", kwargs={"pk": req.pk}
        )  # URL: /api/contact-requests/{id}/decline/
        response = self.client.patch(decline_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "declined")

        req.refresh_from_db()
        self.assertEqual(req.status, "declined")

    def test_unauthorized_action(self):
        """Тест попытки принять/отклонить чужой запрос."""
        self.establish_match(self.user1, self.user2)
        req = ContactRequest.objects.create(
            sender=self.user1, receiver=self.user2, status="sent"
        )

        self.client.force_authenticate(user=self.user3)
        accept_url = reverse("contact-request-accept", kwargs={"pk": req.pk})
        response = self.client.patch(accept_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
