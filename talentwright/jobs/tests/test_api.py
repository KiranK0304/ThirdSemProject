import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.jobs.models import Job
from talentwright.users.models import EmployerProfile, User, VerificationStatus

pytestmark = pytest.mark.django_db


class TestJobCreateAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_verified_employer_can_create_job(self):
        employer_user = User.objects.create_user(
            email="approved-employer@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        EmployerProfile.objects.create(
            user=employer_user,
            company_name="Approved Co",
            verification_status=VerificationStatus.APPROVED,
        )

        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": "approved-employer@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")

        payload = {
            "title": "Backend Engineer",
            "description": "Build APIs and core platform features.",
            "location": "Remote",
            "employment_type": "FULL_TIME",
            "salary_min": "80000.00",
            "salary_max": "120000.00",
            "salary_currency": "USD",
        }

        response = self.client.post(reverse("jobs_api:create"), payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Backend Engineer"
        assert response.data["status"] == "DRAFT"
        assert Job.objects.count() == 1
        job = Job.objects.get()
        assert job.employer.user == employer_user

    def test_unverified_employer_cannot_create_job(self):
        employer_user = User.objects.create_user(
            email="pending-employer@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        EmployerProfile.objects.create(
            user=employer_user,
            company_name="Pending Co",
            verification_status=VerificationStatus.PENDING,
        )

        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": "pending-employer@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")

        payload = {
            "title": "Frontend Engineer",
            "description": "Build client-facing experiences.",
            "employment_type": "FULL_TIME",
        }

        response = self.client.post(reverse("jobs_api:create"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Job.objects.count() == 0

    def test_non_employer_cannot_create_job(self):
        seeker_user = User.objects.create_user(
            email="seeker@example.com",
            password="StrongPassword123!",
            is_active=True,
        )

        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": "seeker@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")

        payload = {
            "title": "QA Engineer",
            "description": "Test product quality.",
            "employment_type": "CONTRACT",
        }

        response = self.client.post(reverse("jobs_api:create"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Job.objects.count() == 0
