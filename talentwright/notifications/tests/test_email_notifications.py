import pytest
from unittest.mock import patch
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.applications.models import Application, ApplicationStatus
from talentwright.jobs.models import Job, JobStatus
from talentwright.notifications.email_services import (
    send_application_rejection_email,
    send_application_shortlist_email,
)
from talentwright.users.models import EmployerProfile, SeekerProfile, User, VerificationStatus

pytestmark = pytest.mark.django_db


class TestApplicationEmailNotifications:
    def setup_method(self):
        self.client = APIClient()

        # Create employer
        self.employer_user = User.objects.create_user(
            email="recruiter@techcorp.com",
            password="StrongPassword123!",
            name="Sarah Recruiter",
            is_active=True,
            is_email_verified=True,
        )
        self.employer_profile = EmployerProfile.objects.create(
            user=self.employer_user,
            company_name="TechCorp Solutions",
            verification_status=VerificationStatus.APPROVED,
        )

        # Create seeker
        self.seeker_user = User.objects.create_user(
            email="candidate@applicant.com",
            password="StrongPassword123!",
            name="Alex Dev",
            is_active=True,
            is_email_verified=True,
        )
        self.seeker_profile = SeekerProfile.objects.create(
            user=self.seeker_user,
            headline="Full Stack Engineer",
        )

        # Create job
        self.job = Job.objects.create(
            employer=self.employer_profile,
            title="Senior Python Engineer",
            description="We are looking for a Senior Python Engineer.",
            status=JobStatus.OPEN,
        )

        # Create application
        self.application = Application.objects.create(
            job=self.job,
            seeker=self.seeker_profile,
            status=ApplicationStatus.SUBMITTED,
        )

    def test_shortlist_email_sent_on_status_change(self):
        """When an employer changes status to SHORTLISTED, an acceptance/shortlist email is sent."""
        self.client.force_authenticate(user=self.employer_user)
        mail.outbox.clear()

        url = reverse("applications_api:employer-application-status-update", kwargs={"pk": self.application.pk})
        response = self.client.patch(url, {"status": ApplicationStatus.SHORTLISTED}, format="json")

        assert response.status_code == status.HTTP_200_OK
        self.application.refresh_from_db()
        assert self.application.status == ApplicationStatus.SHORTLISTED

        # Verify email was dispatched
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert "shortlisted" in email.subject.lower()
        assert "candidate@applicant.com" in email.to
        assert "Senior Python Engineer" in email.body
        assert "TechCorp Solutions" in email.body

    def test_rejection_email_sent_with_note(self):
        """When an employer rejects an applicant with a note, a rejection email with the note is sent."""
        self.client.force_authenticate(user=self.employer_user)
        mail.outbox.clear()

        rejection_note = "We were very impressed by your background, but decided on someone with more AWS experience."
        url = reverse("applications_api:employer-application-status-update", kwargs={"pk": self.application.pk})
        response = self.client.patch(
            url,
            {"status": ApplicationStatus.REJECTED, "rejection_note": rejection_note},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        self.application.refresh_from_db()
        assert self.application.status == ApplicationStatus.REJECTED

        # Verify email was dispatched
        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert "Update regarding your application" in email.subject
        assert "candidate@applicant.com" in email.to
        assert rejection_note in email.body
        assert "Senior Python Engineer" in email.body

    def test_no_email_when_status_does_not_change(self):
        """Updating application without changing status does not trigger redundant emails."""
        self.client.force_authenticate(user=self.employer_user)
        self.application.status = ApplicationStatus.SHORTLISTED
        self.application.save()

        mail.outbox.clear()
        url = reverse("applications_api:employer-application-status-update", kwargs={"pk": self.application.pk})
        # Submit the same status again
        response = self.client.patch(url, {"status": ApplicationStatus.SHORTLISTED}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert len(mail.outbox) == 0

    def test_email_failure_does_not_break_database_update(self):
        """If SMTP delivery raises an unexpected exception, the DB update still persists safely."""
        self.client.force_authenticate(user=self.employer_user)

        with patch("talentwright.notifications.email_services.send_mail", side_effect=Exception("SMTP down")):
            url = reverse("applications_api:employer-application-status-update", kwargs={"pk": self.application.pk})
            response = self.client.patch(url, {"status": ApplicationStatus.SHORTLISTED}, format="json")

            assert response.status_code == status.HTTP_200_OK
            self.application.refresh_from_db()
            assert self.application.status == ApplicationStatus.SHORTLISTED

    def test_unauthorized_user_cannot_update_application_status(self):
        """Another employer or non-employer cannot update the application status."""
        other_user = User.objects.create_user(
            email="other@company.com",
            password="StrongPassword123!",
            is_active=True,
            is_email_verified=True,
        )
        EmployerProfile.objects.create(
            user=other_user,
            company_name="Other Inc",
            verification_status=VerificationStatus.APPROVED,
        )

        self.client.force_authenticate(user=other_user)
        url = reverse("applications_api:employer-application-status-update", kwargs={"pk": self.application.pk})
        response = self.client.patch(url, {"status": ApplicationStatus.SHORTLISTED}, format="json")

        # Returns 404 because get_queryset filters by employer
        assert response.status_code == status.HTTP_404_NOT_FOUND
        self.application.refresh_from_db()
        assert self.application.status == ApplicationStatus.SUBMITTED
