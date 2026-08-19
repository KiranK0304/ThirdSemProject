import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.applications.models import Application, ApplicationStatus
from talentwright.jobs.models import EmploymentType, Job, JobStatus
from talentwright.notifications.models import Notification, NotificationType
from talentwright.users.models import EmployerProfile, SeekerProfile, User, VerificationStatus

pytestmark = pytest.mark.django_db


class TestApplicationNotifications:
    def setup_method(self):
        self.client = APIClient()
        self.employer_user = User.objects.create_user(email="employer@example.com", password="Password123!")
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user,
            company_name="Example Co",
            verification_status=VerificationStatus.APPROVED,
        )
        self.seeker_user = User.objects.create_user(email="seeker@example.com", password="Password123!")
        self.seeker_profile = SeekerProfile.objects.create(user=self.seeker_user)
        self.job = Job.objects.create(
            employer=self.employer_profile,
            title="Backend Engineer",
            description="Build APIs.",
            employment_type=EmploymentType.FULL_TIME,
            status=JobStatus.OPEN,
        )

    def test_application_submission_notifies_employer(self):
        self.client.force_authenticate(self.seeker_user)

        response = self.client.post(
            reverse("applications_api:apply", kwargs={"job_id": self.job.pk}),
            {"cover_letter": "I would love to join."},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Notification.objects.filter(
            recipient=self.employer_user,
            notification_type=NotificationType.APPLICATION_SUBMITTED,
        ).exists()

    def test_application_status_change_notifies_seeker_once(self):
        application = Application.objects.create(job=self.job, seeker=self.seeker_profile)
        self.client.force_authenticate(self.employer_user)

        response = self.client.patch(
            reverse("applications_api:status", kwargs={"pk": application.pk}),
            {"status": ApplicationStatus.UNDER_REVIEW},
            format="json",
        )
        duplicate_response = self.client.patch(
            reverse("applications_api:status", kwargs={"pk": application.pk}),
            {"status": ApplicationStatus.UNDER_REVIEW},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert duplicate_response.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(
            recipient=self.seeker_user,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGED,
        ).count() == 1
