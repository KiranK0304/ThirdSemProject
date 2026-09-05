"""Tests for the end-to-end resume analysis pipeline."""

from decimal import Decimal
import io
from unittest.mock import MagicMock
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
import pytest

from talentwright.applications.models import Application
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.resume_analysis.evaluation_schemas import CriterionEvaluation
from talentwright.resume_analysis.evaluation_schemas import EvaluationScorecard
from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord
from talentwright.resume_analysis.schemas import CandidateContact
from talentwright.resume_analysis.schemas import StructuredResume
from talentwright.resume_analysis.schemas import WorkExperience
from talentwright.resume_analysis.services.llm_client import LLMClient
from talentwright.resume_analysis.services.pipeline import analyze_application
from talentwright.users.models import EmployerProfile
from talentwright.users.models import Resume
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.fixture
def sample_application(db):
    employer_user = User.objects.create(
        email="employer@example.com", name="Employer Inc."
    )
    employer = EmployerProfile.objects.create(
        user=employer_user,
        company_name="Tech Corp",
        verification_status=VerificationStatus.APPROVED,
    )
    job = Job.objects.create(
        employer=employer,
        title="Senior Python Backend Developer",
        description="Looking for an engineer with strong Python, Django, and PostgreSQL experience.",
        status=JobStatus.OPEN,
    )

    seeker_user = User.objects.create(
        email="candidate@example.com", name="Candidate Alice"
    )
    seeker = SeekerProfile.objects.create(user=seeker_user)

    resume_file = SimpleUploadedFile(
        "alice_resume.txt",
        b"Alice Smith\nSoftware Developer\nSkills: Python, Django, PostgreSQL\n5 years experience at Acme Inc.",
        content_type="text/plain",
    )
    resume = Resume.objects.create(
        seeker=seeker,
        title="Alice's Resume",
        file=resume_file,
        is_primary=True,
    )

    return Application.objects.create(
        job=job,
        seeker=seeker,
        resume=resume,
        cover_letter="I am very interested in this Python role.",
    )


@pytest.mark.django_db
def test_pipeline_no_resume(db):
    employer_user = User.objects.create(email="emp2@example.com")
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    job = Job.objects.create(
        employer=employer, title="DevOps Engineer", status=JobStatus.OPEN
    )

    seeker_user = User.objects.create(email="candidate2@example.com")
    seeker = SeekerProfile.objects.create(user=seeker_user)
    app = Application.objects.create(job=job, seeker=seeker, resume=None)

    record = analyze_application(app)
    assert record.status == AnalysisStatus.FAILED
    assert "No resume document found" in record.error_message


@pytest.mark.django_db
def test_pipeline_full_success_with_mock_llm(sample_application):
    mock_llm = MagicMock(spec=LLMClient)

    mock_structured = StructuredResume(
        contact=CandidateContact(name="Alice Smith", email="candidate@example.com"),
        summary="Experienced Software Developer with 5 years in Python and Django.",
        skills=["Python", "Django", "PostgreSQL"],
        total_years_experience=5.0,
        work_experience=[
            WorkExperience(
                company="Acme Inc.",
                title="Software Developer",
                start_date="2019-01",
                end_date="Present",
                is_current=True,
                technologies=["Python", "Django"],
            )
        ],
    )

    mock_scorecard = EvaluationScorecard(
        overall_score=92.50,
        recommendation="STRONG_FIT",
        skills_evaluation=CriterionEvaluation(
            score=95.0,
            reasoning="Exact match with Python and Django.",
            matched_evidence=["Python", "Django", "PostgreSQL"],
        ),
        experience_evaluation=CriterionEvaluation(
            score=90.0,
            reasoning="5 years experience satisfies seniority requirements.",
            matched_evidence=["5 years at Acme Inc."],
        ),
        summary="Strong candidate with high technical match.",
        strengths=["Direct Django experience", "Strong relational DB experience"],
        concerns=[],
    )

    # Return structured resume for parser and scorecard for evaluator
    mock_llm.generate_structured.side_effect = [mock_structured, mock_scorecard]

    record = analyze_application(sample_application.id, llm_client=mock_llm)

    assert record.status == AnalysisStatus.COMPLETED
    assert record.overall_score == Decimal("92.50")
    assert record.recommendation == "STRONG_FIT"
    assert record.structured_resume["contact"]["name"] == "Alice Smith"
    assert record.evaluation_scorecard["overall_score"] == 92.50
    assert "Alice Smith" in record.raw_text
    assert record.error_message == ""


@pytest.mark.django_db
def test_pipeline_fallback_to_seeker_primary_resume(sample_application):
    # Detach resume from application directly, ensure it picks up seeker's primary resume
    app = sample_application
    app.resume = None
    app.save()

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_structured.side_effect = [
        StructuredResume(summary="Developer"),
        EvaluationScorecard(overall_score=70.0, recommendation="MODERATE_FIT"),
    ]

    record = analyze_application(app, llm_client=mock_llm)
    assert record.status == AnalysisStatus.COMPLETED
    assert record.overall_score == Decimal("70.00")
    assert record.recommendation == "MODERATE_FIT"


@pytest.mark.django_db
def test_pipeline_handles_corrupt_file(sample_application):
    # Overwrite file with unsupported extension / corrupted content
    bad_file = SimpleUploadedFile(
        "corrupt.xyz", b"\x00\x01\x02", content_type="application/octet-stream"
    )
    sample_application.resume.file = bad_file
    sample_application.resume.save()

    record = analyze_application(sample_application)
    assert record.status == AnalysisStatus.FAILED
    assert "Unsupported resume file format '.xyz'" in record.error_message
