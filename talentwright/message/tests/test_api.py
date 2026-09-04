# ruff: noqa: S106
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.message.models import ChatRequest
from talentwright.message.models import ChatRequestStatus
from talentwright.message.models import Message
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus

pytestmark = pytest.mark.django_db


class TestMessageAppAPI:
    def setup_method(self):
        self.client = APIClient()

    def _login_seeker(
        self,
        email: str = "seeker@example.com",
        name: str = "Test Seeker",
    ) -> tuple[User, SeekerProfile]:
        user = User.objects.create_user(
            email=email,
            password="StrongPassword123!",
            name=name,
            is_active=True,
        )
        seeker = SeekerProfile.objects.create(
            user=user,
            phone="+1234567890",
            bio="Test Seeker Bio",
        )
        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": email, "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}",
        )
        return user, seeker

    def _login_verified_employer(
        self,
        email: str = "employer@example.com",
        company_name: str = "Acme Corp",
    ) -> tuple[User, EmployerProfile]:
        user = User.objects.create_user(
            email=email,
            password="StrongPassword123!",
            name="Employer Rep",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=user,
            company_name=company_name,
            verification_status=VerificationStatus.APPROVED,
        )
        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": email, "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}",
        )
        return user, employer

    def _create_unverified_employer(
        self,
        email: str = "unverified@example.com",
    ) -> tuple[User, EmployerProfile]:
        user = User.objects.create_user(
            email=email,
            password="StrongPassword123!",
            name="Unverified Employer",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=user,
            company_name="Pending Co",
            verification_status=VerificationStatus.PENDING,
        )
        return user, employer

    # -------------------------------------------------------------------------
    # 1. Seeker Chat Request Creation Tests
    # -------------------------------------------------------------------------

    def test_seeker_can_send_chat_request_to_verified_employer(self):
        _, employer = self._create_unverified_employer("verified-emp@example.com")
        employer.verification_status = VerificationStatus.APPROVED
        employer.save()

        _, seeker = self._login_seeker()

        response = self.client.post(
            reverse("message_api:seeker-request-create"),
            {
                "employer_id": employer.id,
                "initial_message": "Hello, I would love to connect.",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == ChatRequestStatus.PENDING
        assert response.data["initial_message"] == "Hello, I would love to connect."

        chat_req = ChatRequest.objects.get(pk=response.data["id"])
        assert chat_req.seeker == seeker
        assert chat_req.employer == employer
        assert chat_req.status == ChatRequestStatus.PENDING

    def test_seeker_cannot_send_chat_request_to_unverified_employer(self):
        _, unverified_employer = self._create_unverified_employer()
        self._login_seeker()

        response = self.client.post(
            reverse("message_api:seeker-request-create"),
            {"employer_id": unverified_employer.id},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "employer_id" in response.data

    def test_seeker_cannot_send_duplicate_pending_request(self):
        _, employer = self._create_unverified_employer("emp1@example.com")
        employer.verification_status = VerificationStatus.APPROVED
        employer.save()

        _, seeker = self._login_seeker()
        ChatRequest.objects.create(
            seeker=seeker,
            employer=employer,
            status=ChatRequestStatus.PENDING,
        )

        response = self.client.post(
            reverse("message_api:seeker-request-create"),
            {"employer_id": employer.id},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # -------------------------------------------------------------------------
    # 2. Seeker View Separation: Pending Requests vs Approved Chats
    # -------------------------------------------------------------------------

    def test_seeker_pending_and_approved_lists_are_separate(self):
        _, emp1 = self._create_unverified_employer("emp1@example.com")
        emp1.verification_status = VerificationStatus.APPROVED
        emp1.company_name = "Pending Co 1"
        emp1.save()

        _, emp2 = self._create_unverified_employer("emp2@example.com")
        emp2.verification_status = VerificationStatus.APPROVED
        emp2.company_name = "Approved Co 2"
        emp2.save()

        _, seeker = self._login_seeker()

        # emp1 is PENDING
        req1 = ChatRequest.objects.create(
            seeker=seeker,
            employer=emp1,
            status=ChatRequestStatus.PENDING,
            initial_message="Awaiting approval",
        )
        # emp2 is APPROVED
        req2 = ChatRequest.objects.create(
            seeker=seeker,
            employer=emp2,
            status=ChatRequestStatus.APPROVED,
        )

        # Query pending list
        pending_resp = self.client.get(reverse("message_api:seeker-pending-requests"))
        assert pending_resp.status_code == status.HTTP_200_OK
        assert len(pending_resp.data) == 1
        assert pending_resp.data[0]["id"] == req1.id
        assert pending_resp.data[0]["employer"]["company_name"] == "Pending Co 1"
        assert pending_resp.data[0]["status"] == ChatRequestStatus.PENDING

        # Query approved list
        approved_resp = self.client.get(
            reverse("message_api:seeker-approved-conversations"),
        )
        assert approved_resp.status_code == status.HTTP_200_OK
        assert len(approved_resp.data) == 1
        assert approved_resp.data[0]["id"] == req2.id
        assert approved_resp.data[0]["employer"]["company_name"] == "Approved Co 2"
        assert approved_resp.data[0]["status"] == ChatRequestStatus.APPROVED

    # -------------------------------------------------------------------------
    # 3. Employer Review & Approval Flow
    # -------------------------------------------------------------------------

    def test_employer_can_view_and_approve_seeker_request(self):
        seeker_user = User.objects.create_user(
            email="candidate@example.com",
            password="StrongPassword123!",
            name="Alice Seeker",
            is_active=True,
        )
        seeker = SeekerProfile.objects.create(user=seeker_user)

        _, employer = self._login_verified_employer()

        chat_req = ChatRequest.objects.create(
            seeker=seeker,
            employer=employer,
            status=ChatRequestStatus.PENDING,
            initial_message="Hi, I'm Alice!",
        )

        # Employer views incoming requests
        list_resp = self.client.get(reverse("message_api:employer-requests-list"))
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.data) == 1
        assert list_resp.data[0]["seeker"]["user_name"] == "Alice Seeker"

        # Employer approves request
        status_url = reverse(
            "message_api:employer-request-status-update",
            kwargs={"pk": chat_req.pk},
        )
        patch_resp = self.client.patch(
            status_url,
            {"status": ChatRequestStatus.APPROVED},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.data["status"] == ChatRequestStatus.APPROVED

        chat_req.refresh_from_db()
        assert chat_req.status == ChatRequestStatus.APPROVED

    def test_employer_can_reject_seeker_request(self):
        seeker_user = User.objects.create_user(
            email="candidate2@example.com",
            password="StrongPassword123!",
            name="Bob Seeker",
            is_active=True,
        )
        seeker = SeekerProfile.objects.create(user=seeker_user)
        _, employer = self._login_verified_employer()

        chat_req = ChatRequest.objects.create(
            seeker=seeker,
            employer=employer,
            status=ChatRequestStatus.PENDING,
        )

        status_url = reverse(
            "message_api:employer-request-status-update",
            kwargs={"pk": chat_req.pk},
        )
        patch_resp = self.client.patch(
            status_url,
            {"status": ChatRequestStatus.REJECTED},
            format="json",
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.data["status"] == ChatRequestStatus.REJECTED

        chat_req.refresh_from_db()
        assert chat_req.status == ChatRequestStatus.REJECTED

    # -------------------------------------------------------------------------
    # 4. Chat Access Restrictions (Blocked when Pending/Rejected, Allowed when Approved)
    # -------------------------------------------------------------------------

    def test_messaging_blocked_when_request_is_pending(self):
        _, employer = self._create_unverified_employer("emp@example.com")
        employer.verification_status = VerificationStatus.APPROVED
        employer.save()

        _, seeker = self._login_seeker()

        chat_req = ChatRequest.objects.create(
            seeker=seeker,
            employer=employer,
            status=ChatRequestStatus.PENDING,
        )

        msg_url = reverse(
            "message_api:conversation-messages",
            kwargs={"chat_request_id": chat_req.id},
        )

        # Try to send message
        post_resp = self.client.post(
            msg_url,
            {"content": "Hello, are you there?"},
            format="json",
        )
        assert post_resp.status_code == status.HTTP_403_FORBIDDEN
        assert Message.objects.count() == 0

        # Try to view messages
        get_resp = self.client.get(msg_url)
        assert get_resp.status_code == status.HTTP_403_FORBIDDEN

    def test_messaging_blocked_when_request_is_rejected(self):
        _, employer = self._create_unverified_employer("emp-rej@example.com")
        employer.verification_status = VerificationStatus.APPROVED
        employer.save()

        _, seeker = self._login_seeker()

        chat_req = ChatRequest.objects.create(
            seeker=seeker,
            employer=employer,
            status=ChatRequestStatus.REJECTED,
        )

        msg_url = reverse(
            "message_api:conversation-messages",
            kwargs={"chat_request_id": chat_req.id},
        )

        post_resp = self.client.post(
            msg_url,
            {"content": "Can you reconsider?"},
            format="json",
        )
        assert post_resp.status_code == status.HTTP_403_FORBIDDEN

    def test_messaging_allowed_once_approved(self):
        _, employer = self._create_unverified_employer("approved-co@example.com")
        employer.verification_status = VerificationStatus.APPROVED
        employer.company_name = "Approved Co"
        employer.save()

        _, seeker = self._login_seeker(
            "active.seeker@example.com",
            "Active Candidate",
        )

        chat_req = ChatRequest.objects.create(
            seeker=seeker,
            employer=employer,
            status=ChatRequestStatus.APPROVED,
        )

        msg_url = reverse(
            "message_api:conversation-messages",
            kwargs={"chat_request_id": chat_req.id},
        )

        # 1. Seeker sends message
        send_resp = self.client.post(
            msg_url,
            {"content": "Hi! Excited to connect."},
            format="json",
        )
        assert send_resp.status_code == status.HTTP_201_CREATED
        assert send_resp.data["content"] == "Hi! Excited to connect."
        assert send_resp.data["sender_email"] == "active.seeker@example.com"
        assert send_resp.data["is_from_me"] is True

        # 2. Switch login to Employer
        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": "approved-co@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}",
        )

        # Employer reads messages
        list_resp = self.client.get(msg_url)
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.data) == 1
        assert list_resp.data[0]["content"] == "Hi! Excited to connect."
        assert list_resp.data[0]["is_from_me"] is False

        # Employer replies
        reply_resp = self.client.post(
            msg_url,
            {"content": "Welcome! Let us schedule a call."},
            format="json",
        )
        assert reply_resp.status_code == status.HTTP_201_CREATED
        assert reply_resp.data["content"] == "Welcome! Let us schedule a call."
        assert reply_resp.data["is_from_me"] is True

        # Employer marks unread messages as read
        read_resp = self.client.post(
            reverse(
                "message_api:conversation-mark-read",
                kwargs={"chat_request_id": chat_req.id},
            ),
        )
        assert read_resp.status_code == status.HTTP_200_OK
        assert Message.objects.get(content="Hi! Excited to connect.").is_read is True

    # -------------------------------------------------------------------------
    # 5. Permission & Privacy Isolation
    # -------------------------------------------------------------------------

    def test_unrelated_seeker_cannot_access_another_conversation(self):
        _, employer = self._create_unverified_employer("privacy-emp@example.com")
        employer.verification_status = VerificationStatus.APPROVED
        employer.save()

        _, seeker1 = self._login_seeker("seeker1@example.com")
        self._login_seeker("seeker2@example.com")

        chat_req = ChatRequest.objects.create(
            seeker=seeker1,
            employer=employer,
            status=ChatRequestStatus.APPROVED,
        )

        # Seeker 2 is currently logged in, tries to access Seeker 1's conversation
        msg_url = reverse(
            "message_api:conversation-messages",
            kwargs={"chat_request_id": chat_req.id},
        )
        resp = self.client.get(msg_url)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

        post_resp = self.client.post(msg_url, {"content": "Intruding"}, format="json")
        assert post_resp.status_code == status.HTTP_403_FORBIDDEN
