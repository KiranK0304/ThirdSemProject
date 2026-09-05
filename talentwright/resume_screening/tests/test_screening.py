"""Unit and integration tests for the resume_screening app."""
from unittest.mock import patch
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.applications.models import Application
from talentwright.jobs.models import Job, JobStatus
from talentwright.resume_screening.schemas import (
    ContactInfo,
    StructuredResume,
    WorkExperience,
)
from talentwright.resume_screening.services.candidate_builder import (
    build_application_info,
    build_candidate_data,
)
from talentwright.resume_screening.services.pdf_extractor import (
    ExtractionResult,
    extract_text_from_pdf,
)
from talentwright.resume_screening.services.pipeline import (
    _is_degenerate,
    prepare_candidates_for_job,
)
from talentwright.users.models import (
    EmployerProfile,
    Resume,
    SeekerProfile,
    User,
    VerificationStatus,
)

pytestmark = pytest.mark.django_db


class TestPDFExtractor:
    def test_extract_text_from_valid_pdf(self):
        """Verify extraction returns text from an existing seeded resume."""
        resume = Resume.objects.filter(file__icontains="Employee_1").first()
        if not resume:
            pytest.skip("Seed resume not found")
        result = extract_text_from_pdf(resume.file)
        assert result.success is True
        assert result.page_count >= 1
        assert len(result.text) > 500
        assert "Backend" in result.text or "Python" in result.text


class TestCandidateBuilder:
    def test_build_application_info(self):
        user = User.objects.create(email="applicant@test.com", name="Test Applicant")
        seeker = SeekerProfile.objects.create(user=user)
        employer_user = User.objects.create(email="emp@test.com", name="Emp")
        employer = EmployerProfile.objects.create(
            user=employer_user,
            verification_status=VerificationStatus.APPROVED,
        )
        job = Job.objects.create(employer=employer, title="Software Engineer", status=JobStatus.OPEN)
        app = Application.objects.create(job=job, seeker=seeker, cover_letter="Hello hiring team")

        info = build_application_info(app)
        assert info.application_id == app.id
        assert info.job_id == job.id
        assert info.job_title == "Software Engineer"
        assert info.candidate_name == "Test Applicant"
        assert info.candidate_email == "applicant@test.com"
        assert info.cover_letter == "Hello hiring team"


class TestDegenerateCheck:
    def test_empty_resume_is_degenerate(self):
        empty_resume = StructuredResume()
        assert _is_degenerate(empty_resume) is True

    def test_populated_resume_is_not_degenerate(self):
        resume = StructuredResume(
            candidate_name="Alice",
            skills=["Python", "Django"],
        )
        assert _is_degenerate(resume) is False


class TestScreeningAPI:
    def setup_method(self):
        self.client = APIClient()

    def _setup_employer_and_job(self):
        user = User.objects.create_user(
            email="emp_test@example.com",
            password="StrongPassword123!",
            name="Emp Test",
        )
        employer = EmployerProfile.objects.create(
            user=user,
            verification_status=VerificationStatus.APPROVED,
            company_name="Test Company",
        )
        job = Job.objects.create(
            employer=employer,
            title="AI Engineer",
            status=JobStatus.OPEN,
        )
        return user, job

    def test_endpoint_requires_authenticated_employer(self):
        _, job = self._setup_employer_and_job()
        response = self.client.post(f"/api/screening/jobs/{job.id}/prepare/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_seeker_cannot_access_screening(self):
        _, job = self._setup_employer_and_job()
        seeker_user = User.objects.create_user(email="seeker_test@test.com", password="StrongPassword123!")
        SeekerProfile.objects.create(user=seeker_user)
        self.client.force_authenticate(user=seeker_user)

        response = self.client.post(f"/api/screening/jobs/{job.id}/prepare/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch("talentwright.resume_screening.services.pipeline.structure_resume")
    def test_prepare_endpoint_success_with_mock_llm(self, mock_structure):
        """Test the end-to-end API without consuming LLM credits."""
        mock_structure.return_value = StructuredResume(
            candidate_name="Mocked Candidate",
            contact_info=ContactInfo(email="mock@test.com"),
            skills=["Python", "Django", "FastAPI"],
            experience=[
                WorkExperience(
                    company="Mock Corp",
                    title="Backend Engineer",
                    technologies=["Python", "PostgreSQL"],
                )
            ],
        )

        employer_user, job = self._setup_employer_and_job()

        # Create applicant
        applicant_user = User.objects.create_user(email="applicant@test.com", name="Candidate A")
        seeker = SeekerProfile.objects.create(user=applicant_user)
        Application.objects.create(job=job, seeker=seeker, cover_letter="I am passionate about AI")

        self.client.force_authenticate(user=employer_user)

        response = self.client.post(f"/api/screening/jobs/{job.id}/prepare/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["job_id"] == job.id
        assert data["job_title"] == job.title
        assert data["total_applications"] == 1

        cand = data["candidates"][0]
        assert cand["application"]["candidate_name"] == "Candidate A"
        assert cand["application"]["candidate_email"] == "applicant@test.com"
        assert cand["processing"]["has_resume"] is False  # no resume attached to this mock app
