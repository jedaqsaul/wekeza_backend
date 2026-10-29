from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegistrationTests(APITestCase):
    def test_register_success(self):
        url = reverse("auth-register")
        payload = {"name": "Jane Doe", "email": "jane@example.com", "password": "StrongPass123"}
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="jane@example.com").exists())
        self.assertNotIn("password", response.data)

    def test_register_duplicate_email_fails(self):
        User.objects.create_user(email="jane@example.com", password="StrongPass123", name="Jane")
        url = reverse("auth-register")
        payload = {"name": "Jane 2", "email": "jane@example.com", "password": "StrongPass123"}
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password_fails(self):
        url = reverse("auth-register")
        payload = {"name": "Jane", "email": "jane2@example.com", "password": "123"}
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_missing_fields_fails(self):
        url = reverse("auth-register")
        response = self.client.post(url, {"email": "jane3@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com", password="StrongPass123", name="Jane Doe"
        )

    def test_login_success_returns_tokens(self):
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "jane@example.com", "password": "StrongPass123"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_wrong_password_fails(self):
        url = reverse("auth-login")
        response = self.client.post(url, {"email": "jane@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_requires_authentication(self):
        url = reverse("auth-me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_profile_when_authenticated(self):
        login = self.client.post(
            reverse("auth-login"), {"email": "jane@example.com", "password": "StrongPass123"}
        )
        token = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "jane@example.com")
