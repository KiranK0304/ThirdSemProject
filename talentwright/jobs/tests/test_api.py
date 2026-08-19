import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.applications.models import Application
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobBookmark
from talentwright.jobs.models import JobStatus
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus

pytestmark = pytest.mark.django_db


class TestPublicJobSearchAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_public_list_returns_only_open_jobs_from_approved_employers(self):
        approved_user = User.objects.create_user(
            email="approved@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        approved_employer = EmployerProfile.objects.create(
            user=approved_user,
            company_name="Approved Co",
            website="https://approved.example.com",
            verification_status=VerificationStatus.APPROVED,
        )
        open_job = Job.objects.create(
            employer=approved_employer,
            title="Open Role",
            description="Visible to the public.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        Job.objects.create(
            employer=approved_employer,
            title="Draft Role",
            description="Not visible.",
            employment_type="FULL_TIME",
            status=JobStatus.DRAFT,
        )

        pending_user = User.objects.create_user(
            email="pending@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        pending_employer = EmployerProfile.objects.create(
            user=pending_user,
            company_name="Pending Co",
            verification_status=VerificationStatus.PENDING,
        )
        Job.objects.create(
            employer=pending_employer,
            title="Hidden Open Role",
            description="Open but employer not approved.",
            employment_type="CONTRACT",
            status=JobStatus.OPEN,
        )

        response = self.client.get(reverse("jobs_api:list"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Open Role"
        assert response.data[0]["employer"]["company_name"] == "Approved Co"
        assert "user" not in response.data[0]["employer"]
        assert response.data[0]["id"] == open_job.id

    def test_public_detail_returns_only_open_jobs_from_approved_employers(self):
        approved_user = User.objects.create_user(
            email="detail-approved@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        approved_employer = EmployerProfile.objects.create(
            user=approved_user,
            company_name="Detail Approved Co",
            verification_status=VerificationStatus.APPROVED,
        )
        open_job = Job.objects.create(
            employer=approved_employer,
            title="Public Role",
            description="Visible to public detail.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )

        response = self.client.get(reverse("jobs_api:detail", kwargs={"pk": open_job.pk}))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Public Role"
        assert response.data["employer"]["company_name"] == "Detail Approved Co"

    def test_public_detail_hides_non_open_jobs(self):
        approved_user = User.objects.create_user(
            email="hidden-approved@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        approved_employer = EmployerProfile.objects.create(
            user=approved_user,
            company_name="Hidden Approved Co",
            verification_status=VerificationStatus.APPROVED,
        )
        draft_job = Job.objects.create(
            employer=approved_employer,
            title="Draft Role",
            description="Should not be public.",
            employment_type="FULL_TIME",
            status=JobStatus.DRAFT,
        )

        response = self.client.get(reverse("jobs_api:detail", kwargs={"pk": draft_job.pk}))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_public_search_by_keyword(self):
        approved_user = User.objects.create_user(
            email="search-test@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=approved_user,
            company_name="Google Cloud",
            verification_status=VerificationStatus.APPROVED,
        )
        job_py = Job.objects.create(
            employer=employer,
            title="Senior Python Backend Engineer",
            description="Django REST framework development.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        Job.objects.create(
            employer=employer,
            title="React Frontend Developer",
            description="TypeScript and Tailwind.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )

        response = self.client.get(reverse("jobs_api:list"), {"search": "Python"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == job_py.id

    def test_public_filter_by_employment_type_and_location(self):
        approved_user = User.objects.create_user(
            email="filter-test@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=approved_user,
            company_name="Acme Tech",
            verification_status=VerificationStatus.APPROVED,
        )
        job_remote_ft = Job.objects.create(
            employer=employer,
            title="Remote Dev",
            description="Dev work",
            location="Remote, Worldwide",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        Job.objects.create(
            employer=employer,
            title="Onsite Dev",
            description="Dev work",
            location="New York, NY",
            employment_type="CONTRACT",
            status=JobStatus.OPEN,
        )

        # Filter by employment_type
        resp_type = self.client.get(reverse("jobs_api:list"), {"employment_type": "FULL_TIME"})
        assert resp_type.status_code == status.HTTP_200_OK
        assert len(resp_type.data) == 1
        assert resp_type.data[0]["id"] == job_remote_ft.id

        # Filter by location
        resp_loc = self.client.get(reverse("jobs_api:list"), {"location": "Remote"})
        assert resp_loc.status_code == status.HTTP_200_OK
        assert len(resp_loc.data) == 1
        assert resp_loc.data[0]["id"] == job_remote_ft.id

    def test_public_ordering_by_salary(self):
        approved_user = User.objects.create_user(
            email="ordering-test@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=approved_user,
            company_name="Salary Co",
            verification_status=VerificationStatus.APPROVED,
        )
        job_low = Job.objects.create(
            employer=employer,
            title="Junior Dev",
            description="Junior work",
            employment_type="FULL_TIME",
            salary_max=60000,
            status=JobStatus.OPEN,
        )
        job_high = Job.objects.create(
            employer=employer,
            title="Lead Architect",
            description="Architect work",
            employment_type="FULL_TIME",
            salary_max=180000,
            status=JobStatus.OPEN,
        )

        resp = self.client.get(reverse("jobs_api:list"), {"ordering": "-salary_max"})
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 2
        assert resp.data[0]["id"] == job_high.id
        assert resp.data[1]["id"] == job_low.id


class TestSeekerRecommendationsAPI:
    def setup_method(self):
        self.client = APIClient()
        employer_user = User.objects.create_user(
            email="recommendation-employer@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=employer_user,
            company_name="Recommendation Co",
            verification_status=VerificationStatus.APPROVED,
        )
        seeker_user = User.objects.create_user(
            email="recommendation-seeker@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        self.seeker = SeekerProfile.objects.create(user=seeker_user)
        self.seeker_user = seeker_user
        self.history_job = Job.objects.create(
            employer=employer,
            title="Previous Python Role",
            description="Previous role.",
            location="Remote",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        Application.objects.create(job=self.history_job, seeker=self.seeker)
        self.best_match = Job.objects.create(
            employer=employer,
            title="Recommended Remote Role",
            description="Matches type and location.",
            location="Remote - Worldwide",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        self.type_match = Job.objects.create(
            employer=employer,
            title="Recommended Office Role",
            description="Matches employment type.",
            location="New York",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        self.unrelated_job = Job.objects.create(
            employer=employer,
            title="Unrelated Contract Role",
            description="No matching signals.",
            location="Berlin",
            employment_type="CONTRACT",
            status=JobStatus.OPEN,
        )
        self.client.force_authenticate(user=seeker_user)

    def test_recommendations_rank_matching_jobs_and_exclude_applied_jobs(self):
        response = self.client.get(reverse("jobs_api:recommendations"))

        assert response.status_code == status.HTTP_200_OK
        assert [item["id"] for item in response.data] == [
            self.best_match.id,
            self.type_match.id,
            self.unrelated_job.id,
        ]
        assert response.data[0]["match_score"] == 5
        assert response.data[1]["match_score"] == 3
        assert response.data[2]["match_score"] == 0
        assert self.history_job.id not in [item["id"] for item in response.data]

    def test_bookmarked_job_signals_are_used_for_recommendations(self):
        bookmarked_job = Job.objects.create(
            employer=self.history_job.employer,
            title="Bookmarked Type Role",
            description="Matches a bookmarked job type.",
            location="London",
            employment_type="CONTRACT",
            status=JobStatus.OPEN,
        )
        JobBookmark.objects.create(seeker=self.seeker, job=bookmarked_job)
        contract_match = Job.objects.create(
            employer=self.history_job.employer,
            title="Contract Recommendation",
            description="Matches bookmarked type.",
            location="Tokyo",
            employment_type="CONTRACT",
            status=JobStatus.OPEN,
        )

        response = self.client.get(reverse("jobs_api:recommendations"))

        assert response.status_code == status.HTTP_200_OK
        returned_ids = [item["id"] for item in response.data]
        assert contract_match.id in returned_ids
        assert response.data[returned_ids.index(contract_match.id)]["match_score"] == 3

    def test_recommendations_require_a_seeker(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("jobs_api:recommendations"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED



class TestEmployerJobManagementAPI:
    def setup_method(self):
        self.client = APIClient()

    def _create_verified_employer_and_login(self, email: str):
        user = User.objects.create_user(email=email, password="StrongPassword123!", is_active=True)
        employer = EmployerProfile.objects.create(
            user=user,
            company_name=f"{email.split('@')[0]} Co",
            verification_status=VerificationStatus.APPROVED,
        )
        login_resp = self.client.post(
            reverse("auth_api:login"),
            {"email": email, "password": "StrongPassword123!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_resp.data['access']}")
        return user, employer

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

        response = self.client.post(reverse("jobs_api:manage-list"), payload, format="json")

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

        response = self.client.post(reverse("jobs_api:manage-list"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Job.objects.count() == 0

    def test_employer_can_list_only_own_jobs(self):
        _, employer_one = self._create_verified_employer_and_login("employer-one@example.com")
        job_one = Job.objects.create(
            employer=employer_one,
            title="Backend Engineer",
            description="Build APIs.",
            employment_type="FULL_TIME",
        )

        other_user = User.objects.create_user(
            email="employer-two@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        other_employer = EmployerProfile.objects.create(
            user=other_user,
            company_name="Other Co",
            verification_status=VerificationStatus.APPROVED,
        )
        Job.objects.create(
            employer=other_employer,
            title="Frontend Engineer",
            description="Build UI.",
            employment_type="CONTRACT",
        )

        response = self.client.get(reverse("jobs_api:manage-list"))

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == job_one.id

    def test_employer_can_retrieve_own_job(self):
        _, employer = self._create_verified_employer_and_login("retrieve@example.com")
        job = Job.objects.create(
            employer=employer,
            title="Platform Engineer",
            description="Own the platform.",
            employment_type="FULL_TIME",
        )

        response = self.client.get(reverse("jobs_api:manage-detail", kwargs={"pk": job.pk}))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == job.id
        assert response.data["title"] == "Platform Engineer"

    def test_employer_cannot_retrieve_others_job(self):
        _, employer = self._create_verified_employer_and_login("owner@example.com")
        Job.objects.create(
            employer=employer,
            title="Owner Job",
            description="Own job.",
            employment_type="FULL_TIME",
        )

        other_user = User.objects.create_user(
            email="other-owner@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        other_employer = EmployerProfile.objects.create(
            user=other_user,
            company_name="Other Owner Co",
            verification_status=VerificationStatus.APPROVED,
        )
        other_job = Job.objects.create(
            employer=other_employer,
            title="Hidden Job",
            description="Not yours.",
            employment_type="CONTRACT",
        )

        response = self.client.get(reverse("jobs_api:manage-detail", kwargs={"pk": other_job.pk}))

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_employer_can_patch_own_job(self):
        _, employer = self._create_verified_employer_and_login("patch@example.com")
        job = Job.objects.create(
            employer=employer,
            title="Old Title",
            description="Old description.",
            employment_type="FULL_TIME",
        )

        response = self.client.patch(
            reverse("jobs_api:manage-detail", kwargs={"pk": job.pk}),
            {"title": "New Title", "salary_min": "100000.00", "salary_max": "130000.00"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "New Title"
        job.refresh_from_db()
        assert job.title == "New Title"

    def test_employer_can_delete_own_job(self):
        _, employer = self._create_verified_employer_and_login("delete@example.com")
        job = Job.objects.create(
            employer=employer,
            title="Delete Me",
            description="To be removed.",
            employment_type="FULL_TIME",
        )

        response = self.client.delete(reverse("jobs_api:manage-detail", kwargs={"pk": job.pk}))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Job.objects.filter(pk=job.pk).count() == 0

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

        response = self.client.post(reverse("jobs_api:manage-list"), payload, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Job.objects.count() == 0

    def test_employer_can_filter_jobs_by_status(self):
        _, employer = self._create_verified_employer_and_login("filter-status@example.com")
        job_draft = Job.objects.create(
            employer=employer,
            title="Draft Role",
            description="Draft job.",
            employment_type="FULL_TIME",
            status=JobStatus.DRAFT,
        )
        Job.objects.create(
            employer=employer,
            title="Open Role",
            description="Open job.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )

        response = self.client.get(reverse("jobs_api:manage-list"), {"status": "DRAFT"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == job_draft.id


class TestJobBookmarksAPI:
    def setup_method(self):
        self.client = APIClient()
        employer_user = User.objects.create_user(
            email="bookmark-employer@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        employer = EmployerProfile.objects.create(
            user=employer_user,
            company_name="Bookmark Co",
            verification_status=VerificationStatus.APPROVED,
        )
        self.open_job = Job.objects.create(
            employer=employer,
            title="Bookmarkable Role",
            description="A role worth saving.",
            employment_type="FULL_TIME",
            status=JobStatus.OPEN,
        )
        self.seeker_user = User.objects.create_user(
            email="bookmark-seeker@example.com",
            password="StrongPassword123!",
            is_active=True,
        )
        SeekerProfile.objects.create(user=self.seeker_user)
        self.client.force_authenticate(user=self.seeker_user)

    def test_seeker_can_create_list_and_delete_bookmark(self):
        bookmark_url = reverse("jobs_api:bookmark", kwargs={"job_id": self.open_job.pk})

        create_response = self.client.post(bookmark_url)
        assert create_response.status_code == status.HTTP_201_CREATED
        assert create_response.data["job"]["id"] == self.open_job.id

        list_response = self.client.get(reverse("jobs_api:bookmarks"))
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data) == 1
        assert list_response.data[0]["job"]["title"] == "Bookmarkable Role"

        delete_response = self.client.delete(bookmark_url)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        assert self.client.get(reverse("jobs_api:bookmarks")).data == []

    def test_seeker_cannot_bookmark_unavailable_job(self):
        self.open_job.status = JobStatus.CLOSED
        self.open_job.save(update_fields=["status"])

        response = self.client.post(
            reverse("jobs_api:bookmark", kwargs={"job_id": self.open_job.pk}),
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

