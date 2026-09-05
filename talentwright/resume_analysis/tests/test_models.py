"""Tests for ResumeAnalysisRecord database model."""

from decimal import Decimal

import pytest

from talentwright.applications.models import Application
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.mark.django_db
def test_resume_analysis_record_lifecycle():
    employer_user = User.objects.create(email="emp@example.com", name="Employer")
    employer = EmployerProfile.objects.create(
        user=employer_user,
        verification_status=VerificationStatus.APPROVED,
    )
    job = Job.objects.create(
        employer=employer,
        title="Backend Engineer",
        status=JobStatus.OPEN,
    )
    seeker_user = User.objects.create(email="seeker@example.com", name="Seeker")
    seeker = SeekerProfile.objects.create(user=seeker_user)
    application = Application.objects.create(job=job, seeker=seeker)

    # Initial state
    record = ResumeAnalysisRecord.objects.create(
        application=application,
        raw_text="Extracted plain resume text...",
    )
    assert record.status == AnalysisStatus.PENDING
    assert record.overall_score is None
    assert record.structured_resume == {}
    assert record.evaluation_scorecard == {}
    assert "PENDING" in str(record)

    # Update with structured resume and evaluation scorecard
    structured_data = {
        "summary": "Experienced Python Engineer",
        "skills": ["Python", "Django", "PostgreSQL"],
        "total_years_experience": 5.0,
    }
    scorecard_data = {
        "overall_score": 87.50,
        "recommendation": "STRONG_FIT",
        "skills_evaluation": {"score": 90.0, "reasoning": "Strong match"},
        "summary": "Great fit for the position.",
    }

    record.status = AnalysisStatus.COMPLETED
    record.overall_score = Decimal("87.50")
    record.recommendation = "STRONG_FIT"
    record.structured_resume = structured_data
    record.evaluation_scorecard = scorecard_data
    record.save()

    # Re-fetch from DB
    reloaded = ResumeAnalysisRecord.objects.get(id=record.id)
    assert reloaded.status == AnalysisStatus.COMPLETED
    assert reloaded.overall_score == Decimal("87.50")
    assert reloaded.recommendation == "STRONG_FIT"
    assert reloaded.structured_resume["skills"] == ["Python", "Django", "PostgreSQL"]
    assert reloaded.evaluation_scorecard["overall_score"] == 87.50
    assert "87.50" in str(reloaded)

    # Test reverse OneToOne relation from Application
    assert application.resume_analysis == reloaded

    # Test cascade delete: deleting Application deletes ResumeAnalysisRecord
    application.delete()
    assert not ResumeAnalysisRecord.objects.filter(id=record.id).exists()
