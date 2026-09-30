import pytest
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.users.email_verification import (
    generate_verification_token,
    send_verification_email,
    verify_token,
)
from talentwright.users.models import User

pytestmark = pytest.mark.django_db


class TestEmailVerification:
    def setup_method(self):
        self.client = APIClient()

    def test_registration_creates_unverified_user_and_sends_email(self):
        """Registering a new seeker or employer creates an unverified account and sends verification email."""
        url = reverse("auth_api:register")
        payload = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "account_type": "SEEKER",
        }
        mail.outbox.clear()
        response = self.client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email_verification_sent"] is True

        user = User.objects.get(email="newuser@example.com")
        assert user.is_email_verified is False

        # Verify email was sent
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert "Verify your email" in sent_email.subject
        assert "newuser@example.com" in sent_email.to
        assert "/verify-email?token=" in sent_email.body

    def test_unverified_user_cannot_login(self):
        """An unverified user attempting to log in receives a 400 error requiring verification."""
        User.objects.create_user(
            email="unverified@example.com",
            password="StrongPassword123!",
            is_email_verified=False,
        )
        url = reverse("auth_api:login")
        response = self.client.post(
            url,
            {"email": "unverified@example.com", "password": "StrongPassword123!"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_detail = str(response.data)
        assert "verify your email" in error_detail.lower()

    def test_verified_user_can_login(self):
        """A verified user can log in normally."""
        User.objects.create_user(
            email="verified@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )
        url = reverse("auth_api:login")
        response = self.client.post(
            url,
            {"email": "verified@example.com", "password": "StrongPassword123!"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_verify_email_endpoint_success(self):
        """Calling verify-email with a valid signed token verifies the user."""
        user = User.objects.create_user(
            email="toverify@example.com",
            password="StrongPassword123!",
            is_email_verified=False,
        )
        token = generate_verification_token(user)

        url = reverse("auth_api:verify-email")
        response = self.client.post(url, {"token": token}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "verified successfully" in response.data["detail"].lower()

        user.refresh_from_db()
        assert user.is_email_verified is True

    def test_verify_email_already_verified(self):
        """Calling verify-email on an already verified account returns 200 with already verified message."""
        user = User.objects.create_user(
            email="already@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )
        token = generate_verification_token(user)

        url = reverse("auth_api:verify-email")
        response = self.client.post(url, {"token": token}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "already verified" in response.data["detail"].lower()

    def test_verify_email_invalid_token(self):
        """Calling verify-email with an invalid token returns 400 error."""
        url = reverse("auth_api:verify-email")
        response = self.client.post(url, {"token": "invalid-garbage-token"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "invalid or expired" in response.data["detail"].lower()

    def test_verify_email_missing_token(self):
        """Calling verify-email without a token returns 400 error."""
        url = reverse("auth_api:verify-email")
        response = self.client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resend_verification_email_success(self):
        """Resending verification sends a new email for unverified user."""
        user = User.objects.create_user(
            email="resend@example.com",
            password="StrongPassword123!",
            is_email_verified=False,
        )
        mail.outbox.clear()

        url = reverse("auth_api:resend-verification")
        response = self.client.post(url, {"email": "resend@example.com"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 1
        assert "resend@example.com" in mail.outbox[0].to

    def test_resend_verification_nonexistent_email(self):
        """Resending for nonexistent email returns 200 (does not leak email existence)."""
        mail.outbox.clear()
        url = reverse("auth_api:resend-verification")
        response = self.client.post(url, {"email": "ghost@example.com"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 0

    def test_resend_verification_already_verified(self):
        """Resending for an already verified user informs them without sending new email."""
        User.objects.create_user(
            email="done@example.com",
            password="StrongPassword123!",
            is_email_verified=True,
        )
        mail.outbox.clear()

        url = reverse("auth_api:resend-verification")
        response = self.client.post(url, {"email": "done@example.com"}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "already verified" in response.data["detail"].lower()
        assert len(mail.outbox) == 0
