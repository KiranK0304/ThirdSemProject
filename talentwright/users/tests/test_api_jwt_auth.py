import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.users.api.permissions import IsAdmin, IsEmployer, IsSeeker, IsVerifiedEmployer
from talentwright.users.models import EmployerProfile, SeekerProfile, User, VerificationStatus

pytestmark = pytest.mark.django_db


class TestJWTAuthenticationAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_register_employer_success(self):
        url = reverse("auth_api:register")
        payload = {
            "email": "employer@acme.com",
            "name": "Acme Admin",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "account_type": "EMPLOYER",
        }
        response = self.client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "tokens" in response.data
        assert response.data["user"]["email"] == "employer@acme.com"
        assert response.data["user"]["account_type"] == "EMPLOYER"
        assert response.data["user"]["employer_profile"]["verification_status"] == "PENDING"

        user = User.objects.get(email="employer@acme.com")
        assert user.is_employer is True
        assert user.is_seeker is False

    def test_register_seeker_success(self):
        url = reverse("auth_api:register")
        payload = {
            "email": "seeker@example.com",
            "name": "Jane Seeker",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "account_type": "SEEKER",
        }
        response = self.client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["user"]["account_type"] == "SEEKER"
        assert response.data["user"]["seeker_profile"] is not None

        user = User.objects.get(email="seeker@example.com")
        assert user.is_seeker is True
        assert user.is_employer is False

    def test_register_missing_account_type(self):
        url = reverse("auth_api:register")
        payload = {
            "email": "noaccounttype@example.com",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
        }
        response = self.client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "account_type" in response.data

    def test_patch_me_update_employer_profile(self):
        url = reverse("auth_api:register")
        payload = {
            "email": "emp_patch@acme.com",
            "name": "Old Name",
            "password": "StrongPassword123!",
            "password_confirm": "StrongPassword123!",
            "account_type": "EMPLOYER",
        }
        reg_resp = self.client.post(url, payload, format="json")
        access_token = reg_resp.data["tokens"]["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        me_url = reverse("api-me")
        patch_payload = {
            "name": "New Name",
            "employer_profile": {
                "company_name": "Updated Acme Corp",
                "website": "https://updated-acme.com",
            },
        }
        response = self.client.patch(me_url, patch_payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "New Name"
        assert response.data["employer_profile"]["company_name"] == "Updated Acme Corp"
        assert response.data["employer_profile"]["website"] == "https://updated-acme.com"

    def test_permissions_helpers(self):
        # Create Employer
        emp_user = User.objects.create_user(email="emp_perm@example.com", password="Pass", is_active=True)
        emp_prof = EmployerProfile.objects.create(user=emp_user, verification_status=VerificationStatus.PENDING)

        # Create Seeker
        seeker_user = User.objects.create_user(email="seeker_perm@example.com", password="Pass", is_active=True)
        SeekerProfile.objects.create(user=seeker_user)

        # Create Admin
        admin_user = User.objects.create_user(email="admin_perm@example.com", password="Pass", is_staff=True, is_active=True)

        class DummyRequest:
            def __init__(self, user):
                self.user = user

        # Test IsEmployer
        perm = IsEmployer()
        assert perm.has_permission(DummyRequest(emp_user), None) is True
        assert perm.has_permission(DummyRequest(seeker_user), None) is False

        # Test IsVerifiedEmployer
        v_perm = IsVerifiedEmployer()
        assert v_perm.has_permission(DummyRequest(emp_user), None) is False
        emp_prof.verification_status = VerificationStatus.APPROVED
        emp_prof.save()
        assert v_perm.has_permission(DummyRequest(emp_user), None) is True

        # Test IsSeeker
        s_perm = IsSeeker()
        assert s_perm.has_permission(DummyRequest(seeker_user), None) is True
        assert s_perm.has_permission(DummyRequest(emp_user), None) is False

        # Test IsAdmin
        a_perm = IsAdmin()
        assert a_perm.has_permission(DummyRequest(admin_user), None) is True
        assert a_perm.has_permission(DummyRequest(emp_user), None) is False

    def test_admin_employer_list_and_approve_reject_flow(self):
        admin_user = User.objects.create_user(
            email="admin_api@example.com", password="AdminPassword123!", is_staff=True, is_active=True
        )
        emp_user = User.objects.create_user(
            email="emp_api@example.com", password="EmpPassword123!", is_active=True
        )
        emp_prof = EmployerProfile.objects.create(
            user=emp_user, company_name="Test Company", verification_status=VerificationStatus.PENDING
        )

        login_url = reverse("auth_api:login")
        login_resp = self.client.post(
            login_url, {"email": "admin_api@example.com", "password": "AdminPassword123!"}, format="json"
        )
        admin_token = login_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")

        # List pending employers
        list_url = reverse("auth_api:admin-employer-list")
        list_resp = self.client.get(f"{list_url}?status=PENDING")
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.data) == 1
        assert list_resp.data[0]["company_name"] == "Test Company"

        # Approve employer
        approve_url = reverse("auth_api:admin-employer-approve", kwargs={"pk": emp_prof.pk})
        approve_resp = self.client.patch(approve_url)
        assert approve_resp.status_code == status.HTTP_200_OK
        assert approve_resp.data["verification_status"] == "APPROVED"

        # Reject employer
        reject_url = reverse("auth_api:admin-employer-reject", kwargs={"pk": emp_prof.pk})
        reject_resp = self.client.patch(reject_url)
        assert reject_resp.status_code == status.HTTP_200_OK
        assert reject_resp.data["verification_status"] == "REJECTED"

    def test_non_admin_forbidden_on_admin_endpoints(self):
        normal_user = User.objects.create_user(
            email="normal@example.com", password="NormalPassword123!", is_active=True
        )
        login_url = reverse("auth_api:login")
        login_resp = self.client.post(
            login_url, {"email": "normal@example.com", "password": "NormalPassword123!"}, format="json"
        )
        access_token = login_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        list_url = reverse("auth_api:admin-employer-list")
        response = self.client.get(list_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_employer_list_invalid_status_returns_400(self):
        admin_user = User.objects.create_user(
            email="admin_invalid_status@example.com", password="AdminPassword123!", is_staff=True, is_active=True
        )

        login_url = reverse("auth_api:login")
        login_resp = self.client.post(
            login_url,
            {"email": "admin_invalid_status@example.com", "password": "AdminPassword123!"},
            format="json",
        )
        admin_token = login_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")

        list_url = reverse("auth_api:admin-employer-list")
        response = self.client.get(f"{list_url}?status=abc")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "status" in response.data

