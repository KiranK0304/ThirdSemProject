"""Unit and integration tests for the candidate ranking system."""
from unittest.mock import patch
import pytest
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from talentwright.applications.models import Application
from talentwright.jobs.models import Job, JobStatus
from talentwright.resume_screening.models import (
    DEFAULT_CRITERIA_WEIGHTS,
    JobRankingSnapshot,
    JobScoringConfig,
)
from talentwright.resume_screening.schemas import (
    ApplicationInfo,
    CandidateEvaluationResponse,
    CandidateScreeningData,
    ContactInfo,
    CriterionEvaluationItem,
    ProcessingStatus,
    StructuredResume,
)
from talentwright.resume_screening.services.ranker import (
    calculate_final_score,
    evaluate_single_candidate,
    rank_candidates,
)
from talentwright.resume_screening.services.weights import (
    get_job_weights,
    save_job_weights,
    validate_and_normalize_weights,
)
from talentwright.users.models import (
    EmployerProfile,
    SeekerProfile,
    User,
    VerificationStatus,
)

pytestmark = pytest.mark.django_db


# ── 1. Unit Tests for Weight Validation & Calculation ──────────────────


class TestWeightValidation:
    def test_valid_decimal_weights(self):
        weights = {"experience": 0.5, "skills": 0.3, "projects": 0.2}
        normalized = validate_and_normalize_weights(weights)
        assert sum(normalized.values()) == pytest.approx(1.0, abs=1e-4)
        assert normalized["experience"] == 0.5
        assert normalized["skills"] == 0.3
        assert normalized["projects"] == 0.2

    def test_valid_percentage_weights(self):
        weights = {"experience": 50, "skills": 30, "projects": 20}
        normalized = validate_and_normalize_weights(weights)
        assert sum(normalized.values()) == pytest.approx(1.0, abs=1e-4)
        assert normalized["experience"] == 0.5
        assert normalized["skills"] == 0.3
        assert normalized["projects"] == 0.2

    def test_negative_weight_raises_error(self):
        weights = {"experience": -0.2, "skills": 1.2}
        with pytest.raises(ValidationError):
            validate_and_normalize_weights(weights)

    def test_weights_not_summing_to_one_raises_error(self):
        weights = {"experience": 0.3, "skills": 0.3}  # sum is 0.6
        with pytest.raises(ValidationError):
            validate_and_normalize_weights(weights)

    def test_empty_weights_raises_error(self):
        with pytest.raises(ValidationError):
            validate_and_normalize_weights({})

    def test_non_dict_weights_raises_error(self):
        with pytest.raises(ValidationError):
            validate_and_normalize_weights(["experience", 0.5])


class TestFinalScoreCalculation:
    def test_calculate_final_score(self):
        scores = {"experience": 85, "skills": 72, "projects": 90}
        weights = {"experience": 0.50, "skills": 0.20, "projects": 0.30}
        # 85*0.5 (42.5) + 72*0.2 (14.4) + 90*0.3 (27.0) = 83.9
        final_score = calculate_final_score(scores, weights)
        assert final_score == 83.9

    def test_calculate_final_score_with_missing_criterion(self):
        scores = {"experience": 100}
        weights = {"experience": 0.5, "skills": 0.5}
        # 100*0.5 + 0*0.5 = 50.0
        final_score = calculate_final_score(scores, weights)
        assert final_score == 50.0


# ── 2. Unit Tests for Candidate Evaluation and Ranking Logic ───────────


class TestRankingLogic:
    def _create_mock_candidate(self, app_id: int, name: str, has_resume: bool = True) -> CandidateScreeningData:
        app_info = ApplicationInfo(
            application_id=app_id,
            job_id=1,
            job_title="AI Engineer",
            candidate_id=app_id,
            user_id=app_id,
            candidate_name=name,
            candidate_email=f"{name.lower()}@example.com",
            cover_letter="Cover letter",
            application_status="SUBMITTED",
            applied_at="2026-09-05T00:00:00Z",
        )
        resume = (
            StructuredResume(
                candidate_name=name,
                skills=["Python", "FastAPI"],
            )
            if has_resume
            else None
        )
        return CandidateScreeningData(
            application=app_info,
            resume=resume,
            processing=ProcessingStatus(
                success=has_resume,
                has_resume=has_resume,
                resume_extracted=has_resume,
                resume_structured=has_resume,
            ),
        )

    def test_candidate_without_resume_gets_zero_score(self):
        candidate = self._create_mock_candidate(app_id=10, name="NoResumeUser", has_resume=False)
        job = Job(id=1, title="AI Engineer", description="Need Python")
        criteria = ["experience", "skills"]

        scores, details = evaluate_single_candidate(job, candidate, criteria)
        assert scores["experience"] == 0
        assert scores["skills"] == 0
        assert "No resume attached" in details["experience"].reason

    @patch("talentwright.resume_screening.services.ranker.get_llm_provider")
    def test_rank_candidates_sorting(self, mock_provider_getter):
        """Verify candidates are sorted descending by final score."""
        mock_provider = mock_provider_getter.return_value

        # Setup 3 candidates:
        cand_alice = self._create_mock_candidate(app_id=1, name="Alice")
        cand_bob = self._create_mock_candidate(app_id=2, name="Bob")
        cand_charlie = self._create_mock_candidate(app_id=3, name="Charlie", has_resume=False)

        # Mock LLM evaluations:
        # Alice: experience=90, skills=90 -> 90.0
        # Bob:   experience=70, skills=70 -> 70.0
        def mock_generate_structured(prompt, response_schema, temperature=0.0):
            if "Alice" in prompt:
                return CandidateEvaluationResponse(
                    evaluations=[
                        CriterionEvaluationItem(criterion="experience", score=90, reason="9 years experience"),
                        CriterionEvaluationItem(criterion="skills", score=90, reason="Expert Python skills"),
                    ]
                )
            else:
                return CandidateEvaluationResponse(
                    evaluations=[
                        CriterionEvaluationItem(criterion="experience", score=70, reason="3 years experience"),
                        CriterionEvaluationItem(criterion="skills", score=70, reason="Good Python skills"),
                    ]
                )

        mock_provider.generate_structured.side_effect = mock_generate_structured

        # Create employer & job in DB
        employer_user = User.objects.create_user(email="emp_rank@test.com", password="Password123!")
        employer = EmployerProfile.objects.create(user=employer_user, verification_status=VerificationStatus.APPROVED)
        job = Job.objects.create(employer=employer, title="AI Engineer", status=JobStatus.OPEN)

        weights = {"experience": 0.6, "skills": 0.4}
        response = rank_candidates(job, [cand_bob, cand_charlie, cand_alice], weights)

        assert response.total_candidates == 3
        ranked = response.ranked_candidates

        # Alice should be Rank 1 (score 90.0)
        assert ranked[0].rank == 1
        assert ranked[0].candidate_name == "Alice"
        assert ranked[0].final_score == 90.0

        # Bob should be Rank 2 (score 70.0)
        assert ranked[1].rank == 2
        assert ranked[1].candidate_name == "Bob"
        assert ranked[1].final_score == 70.0

        # Charlie should be Rank 3 (score 0.0)
        assert ranked[2].rank == 3
        assert ranked[2].candidate_name == "Charlie"
        assert ranked[2].final_score == 0.0

        # Snapshot saved to DB
        assert JobRankingSnapshot.objects.filter(job=job).count() == 1


# ── 3. Integration Tests for Criteria and Ranking APIs ─────────────────


class TestRankingAPI:
    def setup_method(self):
        self.client = APIClient()
        self.employer_user = User.objects.create_user(
            email="emp_api@example.com",
            password="StrongPassword123!",
            name="Emp Recruiter",
        )
        self.employer = EmployerProfile.objects.create(
            user=self.employer_user,
            verification_status=VerificationStatus.APPROVED,
            company_name="Tech Recruiter Inc",
        )
        self.job = Job.objects.create(
            employer=self.employer,
            title="Senior Python Architect",
            description="Looking for Python and Django specialists.",
            status=JobStatus.OPEN,
        )

    def test_get_criteria_returns_defaults_when_not_customized(self):
        self.client.force_authenticate(user=self.employer_user)
        response = self.client.get(f"/api/screening/jobs/{self.job.id}/criteria/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["job_id"] == self.job.id
        assert data["is_custom"] is False
        assert data["weights"] == DEFAULT_CRITERIA_WEIGHTS

    def test_put_criteria_updates_and_persists_weights(self):
        self.client.force_authenticate(user=self.employer_user)
        new_weights = {"experience": 0.5, "skills": 0.3, "projects": 0.2}
        response = self.client.put(
            f"/api/screening/jobs/{self.job.id}/criteria/",
            {"weights": new_weights},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_custom"] is True
        assert data["weights"]["experience"] == 0.5

        # Verify DB persisted
        saved_config = JobScoringConfig.objects.get(job=self.job)
        assert saved_config.weights["experience"] == 0.5

    def test_put_criteria_rejects_invalid_weights(self):
        self.client.force_authenticate(user=self.employer_user)
        bad_weights = {"experience": 0.2, "skills": 0.2}  # sums to 0.4 != 1.0
        response = self.client.put(
            f"/api/screening/jobs/{self.job.id}/criteria/",
            {"weights": bad_weights},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_rank_returns_404_when_no_snapshot_exists(self):
        self.client.force_authenticate(user=self.employer_user)
        response = self.client.get(f"/api/screening/jobs/{self.job.id}/rank/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("talentwright.resume_screening.services.ranker.get_llm_provider")
    @patch("talentwright.resume_screening.services.pipeline.structure_resume")
    @patch("talentwright.resume_screening.services.pipeline.extract_text_from_pdf")
    def test_post_rank_executes_ranking_and_get_retrieves_it(self, mock_pdf, mock_structure, mock_provider_getter):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from talentwright.resume_screening.services.pdf_extractor import ExtractionResult
        from talentwright.users.models import Resume

        mock_pdf.return_value = ExtractionResult(text="Mock resume text with Python", success=True, page_count=1)
        mock_provider = mock_provider_getter.return_value
        mock_structure.return_value = StructuredResume(candidate_name="Test Dev", skills=["Python"])
        mock_provider.generate_structured.return_value = CandidateEvaluationResponse(
            evaluations=[
                CriterionEvaluationItem(criterion="experience", score=80, reason="Solid exp"),
                CriterionEvaluationItem(criterion="skills", score=85, reason="Python master"),
                CriterionEvaluationItem(criterion="projects", score=75, reason="Good projects"),
                CriterionEvaluationItem(criterion="education", score=70, reason="CS degree"),
            ]
        )

        # Create candidate application with resume
        applicant = User.objects.create_user(email="applicant_ranked@test.com", name="Candidate Top")
        seeker = SeekerProfile.objects.create(user=applicant)
        dummy_file = SimpleUploadedFile("resume.pdf", b"%PDF-dummy", content_type="application/pdf")
        resume = Resume.objects.create(seeker=seeker, file=dummy_file)
        Application.objects.create(job=self.job, seeker=seeker, resume=resume, cover_letter="I am great at Python")

        self.client.force_authenticate(user=self.employer_user)

        # POST /rank/ with custom weights
        post_response = self.client.post(
            f"/api/screening/jobs/{self.job.id}/rank/",
            {"weights": {"experience": 0.4, "skills": 0.3, "projects": 0.2, "education": 0.1}},
            format="json",
        )
        assert post_response.status_code == status.HTTP_200_OK
        data = post_response.json()
        assert data["job_id"] == self.job.id
        assert data["total_candidates"] == 1
        top_cand = data["ranked_candidates"][0]
        assert top_cand["rank"] == 1
        assert top_cand["candidate_name"] == "Candidate Top"
        assert "criteria_scores" in top_cand
        assert "criteria_details" in top_cand
        assert top_cand["final_score"] > 0

        # Now GET /rank/ should retrieve the snapshot
        get_response = self.client.get(f"/api/screening/jobs/{self.job.id}/rank/")
        assert get_response.status_code == status.HTTP_200_OK
        get_data = get_response.json()
        assert get_data["job_id"] == self.job.id
        assert get_data["total_candidates"] == 1
        assert get_data["ranked_candidates"][0]["candidate_name"] == "Candidate Top"

    def test_ranking_uses_cached_evaluations_without_calling_llm(self):
        """Verify that when CandidateScreeningRecord is cached, ranking completes instantly without LLM calls."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        from talentwright.resume_screening.models import CandidateScreeningRecord
        from talentwright.users.models import Resume

        applicant = User.objects.create_user(email="cached_user@test.com", name="Cached User")
        seeker = SeekerProfile.objects.create(user=applicant)
        dummy_file = SimpleUploadedFile("resume.pdf", b"%PDF-dummy", content_type="application/pdf")
        resume = Resume.objects.create(seeker=seeker, file=dummy_file)
        app = Application.objects.create(job=self.job, seeker=seeker, resume=resume)

        # Pre-seed cached evaluations in DB
        CandidateScreeningRecord.objects.create(
            application=app,
            job=self.job,
            resume_file_name=resume.file.name,
            structured_resume={"candidate_name": "Cached User", "skills": ["Python"]},
            criteria_evaluations={
                "experience": {"score": 95, "reason": "10 years exp"},
                "skills": {"score": 90, "reason": "Python expert"},
                "projects": {"score": 85, "reason": "Great projects"},
            },
        )

        self.client.force_authenticate(user=self.employer_user)

        # POST /rank/ with matching criteria - should hit DB cache and return score
        response = self.client.post(
            f"/api/screening/jobs/{self.job.id}/rank/",
            {"weights": {"experience": 0.5, "skills": 0.3, "projects": 0.2}},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        top_cand = data["ranked_candidates"][0]
        assert top_cand["candidate_name"] == "Cached User"
        # 95*0.5 (47.5) + 90*0.3 (27.0) + 85*0.2 (17.0) = 91.5
        assert top_cand["final_score"] == 91.5
        assert top_cand["criteria_scores"]["experience"] == 95

