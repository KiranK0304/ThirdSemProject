import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.jobs.models import Job, JobStatus, EmploymentType
from talentwright.notifications.models import Notification, NotificationType
from talentwright.users.models import EmployerProfile, SeekerProfile, User, VerificationStatus

pytestmark = pytest.mark.django_db


class TestNotificationsAPI:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="user@example.com", password="Password123!")
        self.other_user = User.objects.create_user(email="other@example.com", password="Password123!")

    def test_user_only_sees_own_notifications(self):
        own = Notification.objects.create(
            recipient=self.user,
            notification_type=NotificationType.EMPLOYER_APPROVED,
            title="Own",
            message="Own notification",
        )
        Notification.objects.create(
            recipient=self.other_user,
            notification_type=NotificationType.EMPLOYER_REJECTED,
            title="Other",
            message="Other notification",
        )
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("notifications_api:list"))

        assert response.status_code == status.HTTP_200_OK
        assert [item["id"] for item in response.data] == [own.id]

    def test_mark_all_read_and_unread_count(self):
        for title in ["First", "Second"]:
            Notification.objects.create(
                recipient=self.user,
                notification_type=NotificationType.EMPLOYER_APPROVED,
                title=title,
                message=title,
            )
        self.client.force_authenticate(self.user)

        count_response = self.client.get(reverse("notifications_api:unread-count"))
        assert count_response.data == {"count": 2}

        response = self.client.post(reverse("notifications_api:mark-all-read"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"updated": 2}
        assert Notification.objects.filter(recipient=self.user, is_read=False).count() == 0

    def test_user_cannot_mark_another_users_notification_read(self):
        notification = Notification.objects.create(
            recipient=self.other_user,
            notification_type=NotificationType.EMPLOYER_APPROVED,
            title="Other",
            message="Other notification",
        )
        self.client.force_authenticate(self.user)

        response = self.client.patch(reverse("notifications_api:mark-read", kwargs={"pk": notification.pk}))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        notification.refresh_from_db()
        assert notification.is_read is False


class TestNotificationEvents:
    def setup_method(self):
        self.client = APIClient()

    def test_employer_approval_and_rejection_create_notifications(self):
        admin = User.objects.create_user(email="admin@example.com", password="Password123!", is_staff=True)
        employer = User.objects.create_user(email="employer@example.com", password="Password123!")
        profile = EmployerProfile.objects.create(user=employer, verification_status=VerificationStatus.PENDING)
        self.client.force_authenticate(admin)

        approve_response = self.client.patch(
            reverse("auth_api:admin-employer-approve", kwargs={"pk": profile.pk}),
        )
        duplicate_approve_response = self.client.patch(
            reverse("auth_api:admin-employer-approve", kwargs={"pk": profile.pk}),
        )
        reject_response = self.client.patch(
            reverse("auth_api:admin-employer-reject", kwargs={"pk": profile.pk}),
        )

        assert approve_response.status_code == status.HTTP_200_OK
        assert duplicate_approve_response.status_code == status.HTTP_200_OK
        assert reject_response.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(recipient=employer).count() == 2
        assert set(Notification.objects.filter(recipient=employer).values_list("notification_type", flat=True)) == {
            NotificationType.EMPLOYER_APPROVED,
            NotificationType.EMPLOYER_REJECTED,
        }
