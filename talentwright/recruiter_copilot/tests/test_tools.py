"""Tests for copilot tools and tool registry."""

from decimal import Decimal

import pytest

from talentwright.applications.models import Application
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.recruiter_copilot.tools.candidates import get_top_candidates
from talentwright.recruiter_copilot.tools.descriptions import (
    TOP_CANDIDATES_TOOL_DEFINITION,
)
from talentwright.recruiter_copilot.tools.registry import get_default_registry
from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.fixture
def candidate_pool_setup(db):
    employer_user = User.objects.create_user(
        email="emp_tools@example.com", password="Password123!"
    )
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    job = Job.objects.create(
        employer=employer, title="Python Architect", status=JobStatus.OPEN
    )

    # Candidate 1: 95.0 score
    user1 = User.objects.create_user(email="alice@example.com", name="Alice Smith")
    seeker1 = SeekerProfile.objects.create(user=user1)
    app1 = Application.objects.create(job=job, seeker=seeker1)
    ResumeAnalysisRecord.objects.create(
        application=app1,
        status=AnalysisStatus.COMPLETED,
        overall_score=Decimal("95.00"),
        recommendation="STRONG_FIT",
        structured_resume={
            "skills": ["Python", "Django", "AWS"],
            "total_years_experience": 7.0,
        },
        evaluation_scorecard={
            "summary": "Top tier Python architect with extensive AWS experience."
        },
    )

    # Candidate 2: 70.0 score
    user2 = User.objects.create_user(email="bob@example.com", name="Bob Jones")
    seeker2 = SeekerProfile.objects.create(user=user2)
    app2 = Application.objects.create(job=job, seeker=seeker2)
    ResumeAnalysisRecord.objects.create(
        application=app2,
        status=AnalysisStatus.COMPLETED,
        overall_score=Decimal("70.00"),
        recommendation="MODERATE_FIT",
        structured_resume={
            "skills": ["Python", "Flask"],
            "total_years_experience": 3.0,
        },
        evaluation_scorecard={"summary": "Mid level engineer with Flask experience."},
    )

    # Candidate 3: 88.0 score
    user3 = User.objects.create_user(email="charlie@example.com", name="Charlie Brown")
    seeker3 = SeekerProfile.objects.create(user=user3)
    app3 = Application.objects.create(job=job, seeker=seeker3)
    ResumeAnalysisRecord.objects.create(
        application=app3,
        status=AnalysisStatus.COMPLETED,
        overall_score=Decimal("88.00"),
        recommendation="STRONG_FIT",
        structured_resume={
            "skills": ["Python", "PostgreSQL", "Docker"],
            "total_years_experience": 5.5,
        },
        evaluation_scorecard={
            "summary": "Solid database and containerization background."
        },
    )

    # Candidate 4: Incomplete / Pending (should be excluded)
    user4 = User.objects.create_user(email="dan@example.com", name="Dan Pending")
    seeker4 = SeekerProfile.objects.create(user=user4)
    app4 = Application.objects.create(job=job, seeker=seeker4)
    ResumeAnalysisRecord.objects.create(
        application=app4,
        status=AnalysisStatus.PENDING,
    )

    return {"job": job, "candidates": [app1, app2, app3, app4]}


@pytest.mark.django_db
def test_get_top_candidates_descending(candidate_pool_setup):
    job = candidate_pool_setup["job"]

    # Limit 2 highest
    top2 = get_top_candidates(job_id=job.id, limit=2)
    assert len(top2) == 2
    assert top2[0]["name"] == "Alice Smith"
    assert top2[0]["overall_score"] == 95.0
    assert top2[1]["name"] == "Charlie Brown"
    assert top2[1]["overall_score"] == 88.0

    # Limit 5 (all completed candidates descending)
    top_all = get_top_candidates(job_id=job.id, limit=5)
    assert len(top_all) == 3
    assert [c["name"] for c in top_all] == ["Alice Smith", "Charlie Brown", "Bob Jones"]


@pytest.mark.django_db
def test_get_top_candidates_empty(db):
    employer_user = User.objects.create_user(email="emp_empty@example.com")
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    empty_job = Job.objects.create(
        employer=employer, title="Frontend Dev", status=JobStatus.OPEN
    )

    results = get_top_candidates(job_id=empty_job.id, limit=5)
    assert results == []


@pytest.mark.django_db
def test_tool_registry_execution(candidate_pool_setup):
    job = candidate_pool_setup["job"]
    registry = get_default_registry()

    definitions = registry.get_definitions()
    assert len(definitions) >= 2
    assert any(d["function"]["name"] == "get_top_candidates" for d in definitions)
    assert any(d["function"]["name"] == "search_candidates" for d in definitions)

    # Execute get_top_candidates via registry
    top_output = registry.execute(
        tool_name="get_top_candidates",
        arguments={"limit": 1},
        context={"job_id": job.id},
    )
    assert len(top_output) == 1
    assert top_output[0]["name"] == "Alice Smith"

    # Execute search_candidates via registry
    search_output = registry.execute(
        tool_name="search_candidates",
        arguments={"query": "Django and AWS"},
        context={"job_id": job.id},
    )
    assert isinstance(search_output, list)

    # Execute unknown tool
    with pytest.raises(ValueError, match="is not registered"):
        registry.execute(
            tool_name="non_existent_tool",
            arguments={},
            context={"job_id": job.id},
        )


@pytest.mark.django_db
def test_tools_defensive_argument_coercion(candidate_pool_setup):
    job = candidate_pool_setup["job"]
    registry = get_default_registry()

    # None and invalid string limits should safely fallback to default without raising
    top_with_none = registry.execute(
        tool_name="get_top_candidates",
        arguments={"limit": None},
        context={"job_id": job.id},
    )
    assert len(top_with_none) == 3

    top_with_invalid = registry.execute(
        tool_name="get_top_candidates",
        arguments={"limit": "not_an_int"},
        context={"job_id": job.id},
    )
    assert len(top_with_invalid) == 3

    # search_candidates with missing or empty query should return empty list safely
    search_missing_query = registry.execute(
        tool_name="search_candidates",
        arguments={},
        context={"job_id": job.id},
    )
    assert search_missing_query == []

    search_empty_query = registry.execute(
        tool_name="search_candidates",
        arguments={"query": "   ", "limit": None},
        context={"job_id": job.id},
    )
    assert search_empty_query == []
