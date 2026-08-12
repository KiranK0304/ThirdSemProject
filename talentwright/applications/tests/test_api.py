import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.applications.models import Application
from talentwright.applications.models import ApplicationStatus
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.users.models import EmployerProfile
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
