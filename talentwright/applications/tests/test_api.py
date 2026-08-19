from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.applications.models import Application
from talentwright.applications.models import ApplicationStatus
from talentwright.applications.models import Interview
from talentwright.applications.models import InterviewStatus
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.users.models import EmployerProfile
from talentwright.users.models import Resume
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus

pytestmark = pytest.mark.django_db


class TestJobApplicationAPI:
    def setup_method(self):
        self.client = APIClient()

    def _create_approved_employer_job(self, *, title: str = "Open Role", status: str = JobStatus.OPEN) -> Job:
        employer_user = User.objects.create_user(
            email="employer@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=employer_user,
            company_name="Approved Co",
            verification_status=VerificationStatus.APPROVED,
        )
        return Job.objects.create(
            employer=employer,
            title=title,
            description="A public job.",
            employment_type="FULL_TIME",
            status=status,
        )

    def _login_seeker(self, email: str = "seeker@example.com") -> User:
        user = User.objects.create_user(
            email=email,
            password="StrongPassword123!",
            is_active=True,
        )
        SeekerProfile.objects.create(user=user, phone="+10000000000", bio="Candidate bio")
        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": email, "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        return user

    def _login_verified_employer(self, email: str = "verified-employer@example.com") -> tuple[User, EmployerProfile]:
        user = User.objects.create_user(
            email=email,
            password="StrongPassword123!",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=user,
            company_name="Verified Co",
            verification_status=VerificationStatus.APPROVED,
        )
        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": email, "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        return user, employer

    def test_seeker_can_apply_to_open_job(self):
        job = self._create_approved_employer_job()
        seeker = self._login_seeker()

        response = self.client.post(
            reverse("applications_api:job-apply", kwargs={"job_id": job.pk}),
            {"cover_letter": "I would love to join."},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == ApplicationStatus.SUBMITTED
        assert response.data["job"]["id"] == job.id
        assert response.data["seeker"]["user_email"] == seeker.email
        assert Application.objects.filter(job=job, seeker=seeker.seeker_profile).count() == 1

    def test_seeker_cannot_apply_twice_to_same_job(self):
        job = self._create_approved_employer_job()
        seeker = self._login_seeker()
        Application.objects.create(job=job, seeker=seeker.seeker_profile, cover_letter="Already here.")

        response = self.client.post(
            reverse("applications_api:job-apply", kwargs={"job_id": job.pk}),
            {"cover_letter": "Second try."},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Application.objects.filter(job=job, seeker=seeker.seeker_profile).count() == 1

    def test_seeker_cannot_apply_to_closed_job(self):
        job = self._create_approved_employer_job(status=JobStatus.CLOSED)
        self._login_seeker()

        response = self.client.post(
            reverse("applications_api:job-apply", kwargs={"job_id": job.pk}),
            {"cover_letter": "I am interested."},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Application.objects.count() == 0

    def test_non_seeker_cannot_apply(self):
        job = self._create_approved_employer_job()
        user, _ = self._login_verified_employer()

        response = self.client.post(
            reverse("applications_api:job-apply", kwargs={"job_id": job.pk}),
            {"cover_letter": "Trying to apply."},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not hasattr(user, "seeker_profile")
        assert Application.objects.count() == 0

    def test_job_owner_can_list_applications_for_job(self):
        owner_user = User.objects.create_user(
            email="owner-list@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        owner_employer = EmployerProfile.objects.create(
            user=owner_user,
            company_name="Owner List Co",
            verification_status=VerificationStatus.APPROVED,
        )
        job = Job.objects.create(
            employer=owner_employer,
            title="Owner Role",
            description="Owner job.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        seeker_user = User.objects.create_user(email="seeker1@example.com", password="StrongPassword123!", is_active=True)
        seeker_profile = SeekerProfile.objects.create(user=seeker_user)
        Application.objects.create(job=job, seeker=seeker_profile, cover_letter="First application.")

        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": "owner-list@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")

        response = self.client.get(reverse("applications_api:job-applications", kwargs={"job_id": job.pk}))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["job"]["id"] == job.id
        assert response.data[0]["seeker"]["user_email"] == seeker_user.email

    def test_non_owner_cannot_list_job_applications(self):
        job = self._create_approved_employer_job()
        another_user, another_employer = self._login_verified_employer("other-employer@example.com")

        response = self.client.get(reverse("applications_api:job-applications", kwargs={"job_id": job.pk}))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert another_employer.user == another_user

    def test_employer_can_list_all_applications_for_owned_jobs(self):
        employer_user = User.objects.create_user(
            email="owner@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=employer_user,
            company_name="Owner Co",
            verification_status=VerificationStatus.APPROVED,
        )

        job_one = Job.objects.create(
            employer=employer,
            title="Role One",
            description="Job one.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        job_two = Job.objects.create(
            employer=employer,
            title="Role Two",
            description="Job two.",
            employment_type="CONTRACT",
            status=JobStatus.OPEN,
        )

        seeker_one = User.objects.create_user(email="seeker-one@example.com", password="StrongPassword123!", is_active=True)
        seeker_two = User.objects.create_user(email="seeker-two@example.com", password="StrongPassword123!", is_active=True)
        profile_one = SeekerProfile.objects.create(user=seeker_one)
        profile_two = SeekerProfile.objects.create(user=seeker_two)
        Application.objects.create(job=job_one, seeker=profile_one, cover_letter="For job one.")
        Application.objects.create(job=job_two, seeker=profile_two, cover_letter="For job two.")

        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": "owner@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")

        response = self.client.get(reverse("applications_api:employer-applications"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        returned_job_ids = {item["job"]["id"] for item in response.data}
        assert returned_job_ids == {job_one.id, job_two.id}

    def test_job_owner_can_update_application_status(self):
        owner_user, owner_employer = self._login_verified_employer("status-owner@example.com")
        job = Job.objects.create(
            employer=owner_employer,
            title="Owner Role",
            description="Owner job.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        seeker_user = User.objects.create_user(email="seeker-status@example.com", password="StrongPassword123!", is_active=True)
        seeker_profile = SeekerProfile.objects.create(user=seeker_user)
        application = Application.objects.create(job=job, seeker=seeker_profile, status=ApplicationStatus.SUBMITTED)

        response = self.client.patch(
            reverse("applications_api:employer-application-status-update", kwargs={"pk": application.pk}),
            {"status": ApplicationStatus.SHORTLISTED},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == ApplicationStatus.SHORTLISTED
        application.refresh_from_db()
        assert application.status == ApplicationStatus.SHORTLISTED

    def test_non_owner_cannot_update_application_status(self):
        job = self._create_approved_employer_job()
        seeker_user = User.objects.create_user(email="seeker-other@example.com", password="StrongPassword123!", is_active=True)
        seeker_profile = SeekerProfile.objects.create(user=seeker_user)
        application = Application.objects.create(job=job, seeker=seeker_profile, status=ApplicationStatus.SUBMITTED)

        self._login_verified_employer("different-employer@example.com")

        response = self.client.patch(
            reverse("applications_api:employer-application-status-update", kwargs={"pk": application.pk}),
            {"status": ApplicationStatus.SHORTLISTED},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        application.refresh_from_db()
        assert application.status == ApplicationStatus.SUBMITTED


    def test_invalid_status_rejected_for_employer_update(self):
        owner_user, owner_employer = self._login_verified_employer("status-invalid@example.com")
        job = Job.objects.create(
            employer=owner_employer,
            title="Owner Role",
            description="Owner job.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        seeker_user = User.objects.create_user(email="seeker-inv@example.com", password="StrongPassword123!", is_active=True)
        seeker_profile = SeekerProfile.objects.create(user=seeker_user)
        application = Application.objects.create(job=job, seeker=seeker_profile, status=ApplicationStatus.SUBMITTED)

        response = self.client.patch(
            reverse("applications_api:employer-application-status-update", kwargs={"pk": application.pk}),
            {"status": "INVALID_STATUS"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_seeker_cannot_update_application_status(self):
        job = self._create_approved_employer_job()
        seeker_user = self._login_seeker()
        application = Application.objects.create(job=job, seeker=seeker_user.seeker_profile, status=ApplicationStatus.SUBMITTED)

        response = self.client.patch(
            reverse("applications_api:employer-application-status-update", kwargs={"pk": application.pk}),
            {"status": ApplicationStatus.SHORTLISTED},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_seeker_can_list_own_applications(self):
        job_one = self._create_approved_employer_job(title="Job Alpha")
        job_two = Job.objects.create(
            employer=job_one.employer,
            title="Job Beta",
            description="Job Beta desc.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )

        seeker_user = self._login_seeker("my-applications@example.com")
        other_user = User.objects.create_user(email="other-seeker@example.com", password="StrongPassword123!", is_active=True)
        other_seeker = SeekerProfile.objects.create(user=other_user)

        app_one = Application.objects.create(job=job_one, seeker=seeker_user.seeker_profile, cover_letter="App 1")
        app_two = Application.objects.create(job=job_two, seeker=seeker_user.seeker_profile, cover_letter="App 2")
        Application.objects.create(job=job_one, seeker=other_seeker, cover_letter="Other seeker app")

        response = self.client.get(reverse("applications_api:seeker-applications"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        returned_ids = {item["id"] for item in response.data}
        assert returned_ids == {app_one.id, app_two.id}

    def test_seeker_can_retrieve_own_application_detail(self):
        job = self._create_approved_employer_job()
        seeker_user = self._login_seeker("seeker-detail@example.com")
        application = Application.objects.create(job=job, seeker=seeker_user.seeker_profile, cover_letter="Detail check")

        response = self.client.get(reverse("applications_api:seeker-application-detail", kwargs={"pk": application.pk}))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == application.id
        assert response.data["cover_letter"] == "Detail check"
        assert response.data["job"]["id"] == job.id

    def test_seeker_can_withdraw_own_application(self):
        job = self._create_approved_employer_job()
        seeker_user = self._login_seeker("withdraw-seeker@example.com")
        application = Application.objects.create(job=job, seeker=seeker_user.seeker_profile, cover_letter="To withdraw")

        response = self.client.delete(reverse("applications_api:seeker-application-detail", kwargs={"pk": application.pk}))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Application.objects.filter(pk=application.pk).exists()

    def test_seeker_cannot_retrieve_or_withdraw_other_seeker_application(self):
        job = self._create_approved_employer_job()
        other_user = User.objects.create_user(email="other-person@example.com", password="StrongPassword123!", is_active=True)
        other_seeker = SeekerProfile.objects.create(user=other_user)
        application = Application.objects.create(job=job, seeker=other_seeker, cover_letter="Other app")

        self._login_seeker("me-seeker@example.com")

        get_resp = self.client.get(reverse("applications_api:seeker-application-detail", kwargs={"pk": application.pk}))
        assert get_resp.status_code == status.HTTP_404_NOT_FOUND

        del_resp = self.client.delete(reverse("applications_api:seeker-application-detail", kwargs={"pk": application.pk}))
        assert del_resp.status_code == status.HTTP_404_NOT_FOUND
        assert Application.objects.filter(pk=application.pk).exists()

    def test_employer_cannot_access_seeker_applications_endpoint(self):
        self._login_verified_employer("emp-no-access@example.com")

        response = self.client.get(reverse("applications_api:seeker-applications"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_seeker_can_apply_with_chosen_resume(self):
        job = self._create_approved_employer_job()
        seeker_user = self._login_seeker("attach-resume@example.com")
        resume = Resume.objects.create(
            seeker=seeker_user.seeker_profile,
            title="Tailored Resume",
            file="resumes/2026/08/tailored.pdf",
        )

        response = self.client.post(
            reverse("applications_api:job-apply", kwargs={"job_id": job.pk}),
            {"cover_letter": "With resume", "resume_id": resume.id},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["resume"]["id"] == resume.id
        assert response.data["resume"]["title"] == "Tailored Resume"
        app = Application.objects.get(job=job, seeker=seeker_user.seeker_profile)
        assert app.resume == resume

    def test_seeker_cannot_apply_with_another_users_resume(self):
        job = self._create_approved_employer_job()
        other_user = User.objects.create_user(email="other-r@example.com", password="StrongPassword123!", is_active=True)
        other_seeker = SeekerProfile.objects.create(user=other_user)
        other_resume = Resume.objects.create(
            seeker=other_seeker,
            title="Other Resume",
            file="resumes/2026/08/other.pdf",
        )

        self._login_seeker("my-r@example.com")

        response = self.client.post(
            reverse("applications_api:job-apply", kwargs={"job_id": job.pk}),
            {"cover_letter": "Stealing resume", "resume_id": other_resume.id},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Application.objects.count() == 0

    def test_employer_sees_attached_resume_on_applications_list(self):
        owner_user, owner_employer = self._login_verified_employer("employer-resume-view@example.com")
        job = Job.objects.create(
            employer=owner_employer,
            title="Resume View Job",
            description="Looking for resumes",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        seeker_user = User.objects.create_user(email="applicant-resume@example.com", password="StrongPassword123!", is_active=True)
        seeker_profile = SeekerProfile.objects.create(user=seeker_user)
        resume = Resume.objects.create(
            seeker=seeker_profile,
            title="Candidate Resume",
            file="resumes/2026/08/candidate.pdf",
        )
        Application.objects.create(job=job, seeker=seeker_profile, resume=resume, cover_letter="Hi")

        response = self.client.get(reverse("applications_api:job-applications", kwargs={"job_id": job.pk}))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["resume"]["id"] == resume.id
        assert response.data[0]["resume"]["title"] == "Candidate Resume"


class TestInterviewSchedulingAPI:
    def setup_method(self):
        self.client = APIClient()
        employer_user = User.objects.create_user(
            email="interview-employer@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.employer = EmployerProfile.objects.create(
            user=employer_user,
            company_name="Interview Co",
            verification_status=VerificationStatus.APPROVED,
        )
        self.job = Job.objects.create(
            employer=self.employer,
            title="Interview Role",
            description="Role with an interview.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        seeker_user = User.objects.create_user(
            email="interview-seeker@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.seeker = SeekerProfile.objects.create(user=seeker_user)
        self.application = Application.objects.create(
            job=self.job,
            seeker=self.seeker,
            status=ApplicationStatus.SHORTLISTED,
        )
        self.employer_user = employer_user
        self.seeker_user = seeker_user

    def _authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_employer_can_schedule_and_seeker_can_view_interview(self):
        self._authenticate(self.employer_user)
        schedule_url = reverse(
            "applications_api:employer-interview-create",
            kwargs={"application_id": self.application.pk},
        )
        scheduled_at = timezone.now() + timedelta(days=1)

        response = self.client.post(
            schedule_url,
            {
                "scheduled_at": scheduled_at.isoformat(),
                "duration_minutes": 45,
                "meeting_url": "https://meet.example.com/interview",
                "notes": "Please prepare a short project overview.",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == InterviewStatus.SCHEDULED
        assert Interview.objects.filter(application=self.application).count() == 1

        self._authenticate(self.seeker_user)
        response = self.client.get(reverse("applications_api:seeker-interviews"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["job_title"] == "Interview Role"

    def test_employer_can_cancel_interview_and_cannot_schedule_twice(self):
        interview = Interview.objects.create(
            application=self.application,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        self._authenticate(self.employer_user)

        update_response = self.client.patch(
            reverse("applications_api:employer-interview-update", kwargs={"pk": interview.pk}),
            {"status": InterviewStatus.CANCELLED},
            format="json",
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["status"] == InterviewStatus.CANCELLED

        duplicate_response = self.client.post(
            reverse(
                "applications_api:employer-interview-create",
                kwargs={"application_id": self.application.pk},
            ),
            {
                "scheduled_at": (timezone.now() + timedelta(days=2)).isoformat(),
            },
            format="json",
        )
        assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST

    def test_only_shortlisted_applications_can_be_scheduled(self):
        self.application.status = ApplicationStatus.UNDER_REVIEW
        self.application.save(update_fields=["status"])
        self._authenticate(self.employer_user)

        response = self.client.post(
            reverse(
                "applications_api:employer-interview-create",
                kwargs={"application_id": self.application.pk},
            ),
            {"scheduled_at": (timezone.now() + timedelta(days=1)).isoformat()},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND



