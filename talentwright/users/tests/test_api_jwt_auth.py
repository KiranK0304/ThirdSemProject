import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.users.models import User

pytestmark = pytest.mark.django_db


class TestJWTAuthenticationAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_register_user_success(self):
        url = reverse("auth_api:register")
        payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }
        response = self.client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]
        assert response.data["user"]["email"] == "newuser@example.com"
        assert response.data["user"]["name"] == "New User"

        user = User.objects.get(email="newuser@example.com")
        assert user.is_active is True

    def test_register_password_mismatch(self):
        url = reverse("auth_api:register")
        payload = {
            "email": "mismatch@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }
        response = self.client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password_confirm" in response.data

    def test_login_success(self):
        user = User.objects.create_user(
            email="loginuser@example.com",
            password="LoginPassword123!",
            name="Login User",
            is_active=True,
        )
        url = reverse("auth_api:login")
        payload = {
            "email": "loginuser@example.com",
            "password": "LoginPassword123!",
        }
        response = self.client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert response.data["user"]["id"] == user.id

    def test_login_invalid_credentials(self):
        User.objects.create_user(
            email="loginuser2@example.com",
            password="LoginPassword123!",
            is_active=True,
        )
        url = reverse("auth_api:login")
        payload = {
            "email": "loginuser2@example.com",
            "password": "WrongPassword123!",
        }
        response = self.client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticated_me_endpoint_success(self):
        user = User.objects.create_user(
            email="meuser@example.com",
            password="MePassword123!",
            name="Me User",
            is_active=True,
        )
        login_url = reverse("auth_api:login")
        login_resp = self.client.post(
            login_url,
            {"email": "meuser@example.com", "password": "MePassword123!"},
            format="json",
        )
        access_token = login_resp.data["access"]

        me_url = reverse("api-me")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = self.client.get(me_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "meuser@example.com"
        assert response.data["name"] == "Me User"

    def test_me_endpoint_unauthorized(self):
        me_url = reverse("api-me")
        response = self.client.get(me_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_flow(self):
        user = User.objects.create_user(
            email="refreshuser@example.com",
            password="RefreshPassword123!",
            is_active=True,
        )
        login_url = reverse("auth_api:login")
        login_resp = self.client.post(
            login_url,
            {"email": "refreshuser@example.com", "password": "RefreshPassword123!"},
            format="json",
        )
        refresh_token = login_resp.data["refresh"]

        refresh_url = reverse("auth_api:refresh")
        response = self.client.post(
            refresh_url, {"refresh": refresh_token}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data  # Rotated refresh token

    def test_logout_blacklists_token(self):
        user = User.objects.create_user(
            email="logoutuser@example.com",
            password="LogoutPassword123!",
            is_active=True,
        )
        login_url = reverse("auth_api:login")
        login_resp = self.client.post(
            login_url,
            {"email": "logoutuser@example.com", "password": "LogoutPassword123!"},
            format="json",
        )
        access_token = login_resp.data["access"]
        refresh_token = login_resp.data["refresh"]

        # Authenticate and call logout
        logout_url = reverse("auth_api:logout")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        logout_resp = self.client.post(
            logout_url, {"refresh": refresh_token}, format="json"
        )

        assert logout_resp.status_code == status.HTTP_200_OK

        # Try to use the blacklisted refresh token to obtain a new access token
        refresh_url = reverse("auth_api:refresh")
        self.client.credentials()  # clear auth header
        refresh_resp = self.client.post(
            refresh_url, {"refresh": refresh_token}, format="json"
        )

        assert refresh_resp.status_code == status.HTTP_401_UNAUTHORIZED
