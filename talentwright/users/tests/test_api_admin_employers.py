import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from talentwright.users.models import EmployerProfile, SeekerProfile, User, VerificationStatus

pytestmark = pytest.mark.django_db


class TestAdminEmployerManagementAPI:
    def setup_method(self):
        self.client = APIClient()

        # Admin user
        self.admin_user = User.objects.create_superuser(
            email="superadmin@talentwright.ai",
            password="AdminPassword123!",
            name="Super Admin",
            is_email_verified=True,
        )

        # Seeker user
        self.seeker_user = User.objects.create_user(
            email="candidate@example.com",
            password="Password123!",
            name="Test Seeker",
            is_email_verified=True,
        )
        self.seeker_profile = SeekerProfile.objects.create(
            user=self.seeker_user,
            phone="+1234567890",
            headline="Software Engineer",
        )

        # Employer 1: Pending
        self.employer_user1 = User.objects.create_user(
            email="emp1@company.com",
            password="Password123!",
            name="Employer One",
            is_email_verified=True,
        )
        self.employer_profile1 = EmployerProfile.objects.create(
            user=self.employer_user1,
            company_name="Acme Corp",
            website="https://acme.com",
            company_size="51-200",
            headquarters="San Francisco, CA",
            description="Innovative cloud solutions.",
            verification_status=VerificationStatus.PENDING,
        )

        # Employer 2: Approved
        self.employer_user2 = User.objects.create_user(
            email="emp2@global.com",
            password="Password123!",
            name="Employer Two",
            is_email_verified=True,
        )
        self.employer_profile2 = EmployerProfile.objects.create(
            user=self.employer_user2,
            company_name="Global Tech",
            website="https://globaltech.io",
            company_size="500+",
            headquarters="New York, NY",
            verification_status=VerificationStatus.APPROVED,
        )

    def _auth_as(self, user):
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_admin_can_list_all_employers(self):
        self._auth_as(self.admin_user)
        url = reverse("auth_api:admin-employer-list")
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        
        # Verify serialized fields include company_size and headquarters
        acme = next(e for e in response.data if e["id"] == self.employer_profile1.id)
        assert acme["company_name"] == "Acme Corp"
        assert acme["company_size"] == "51-200"
        assert acme["headquarters"] == "San Francisco, CA"
        assert acme["website"] == "https://acme.com"
        assert acme["verification_status"] == "PENDING"
        assert acme["user_email"] == "emp1@company.com"

    def test_admin_can_filter_employers_by_status(self):
        self._auth_as(self.admin_user)
        url = reverse("auth_api:admin-employer-list")
        response = self.client.get(url, {"status": "PENDING"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == self.employer_profile1.id

    def test_admin_can_approve_employer(self):
        self._auth_as(self.admin_user)
        url = reverse("auth_api:admin-employer-approve", kwargs={"pk": self.employer_profile1.id})
        response = self.client.patch(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["verification_status"] == "APPROVED"
        assert response.data["company_size"] == "51-200"
        assert response.data["headquarters"] == "San Francisco, CA"

        self.employer_profile1.refresh_from_db()
        assert self.employer_profile1.verification_status == VerificationStatus.APPROVED

    def test_admin_can_reject_employer(self):
        self._auth_as(self.admin_user)
        url = reverse("auth_api:admin-employer-reject", kwargs={"pk": self.employer_profile2.id})
        response = self.client.patch(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["verification_status"] == "REJECTED"

        self.employer_profile2.refresh_from_db()
        assert self.employer_profile2.verification_status == VerificationStatus.REJECTED

    def test_non_admin_cannot_access_admin_employer_endpoints(self):
        # Seeker cannot access
        self._auth_as(self.seeker_user)
        url = reverse("auth_api:admin-employer-list")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        approve_url = reverse("auth_api:admin-employer-approve", kwargs={"pk": self.employer_profile1.id})
        response = self.client.patch(approve_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_anonymous_user_cannot_access_admin_employer_endpoints(self):
        url = reverse("auth_api:admin-employer-list")
        response = self.client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
