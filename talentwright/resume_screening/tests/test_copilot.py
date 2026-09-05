"""Tests for AI Recruiter Agent Copilot service and endpoint."""
from unittest.mock import MagicMock, patch
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from talentwright.applications.models import Application
from talentwright.jobs.models import Job, JobStatus
from talentwright.resume_screening.models import (
    CandidateScreeningRecord,
    JobRankingSnapshot,
)
from talentwright.resume_screening.schemas import CopilotMessage
from talentwright.resume_screening.services.copilot import (
    build_recruiter_agent_context,
    execute_copilot_command,
)
from talentwright.resume_screening.services.llm_provider import LLMProviderError
from talentwright.users.models import (
    EmployerProfile,
    SeekerProfile,
    User,
    VerificationStatus,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def employer_user():
    user = User.objects.create_user(
        email="recruiter@example.com",
        password="password123",
        name="Recruiter",
    )
    EmployerProfile.objects.create(
        user=user,
        company_name="Acme Tech",
        verification_status=VerificationStatus.APPROVED,
    )
    return user


@pytest.fixture
def other_employer_user():
    user = User.objects.create_user(
        email="other@example.com",
        password="password123",
        name="Other Employer",
    )
    EmployerProfile.objects.create(
        user=user,
        company_name="Beta Corp",
        verification_status=VerificationStatus.APPROVED,
    )
    return user


@pytest.fixture
def seeker_user():
    user = User.objects.create_user(
        email="seeker@example.com",
        password="password123",
        name="Seeker",
    )
    SeekerProfile.objects.create(user=user)
    return user


@pytest.fixture
def active_job(employer_user):
    return Job.objects.create(
        employer=employer_user.employer_profile,
        title="Senior Python & React Engineer",
        description="Looking for an experienced full-stack engineer with 5+ years Python, React, PostgreSQL.",
        status=JobStatus.OPEN,
    )


@pytest.fixture
def seeded_candidates(active_job):
    # Candidate 1: Alex Rivera
    u1 = User.objects.create_user(email="alex@example.com", password="pwd", name="Alex Rivera")
    p1 = SeekerProfile.objects.create(user=u1)
    app1 = Application.objects.create(job=active_job, seeker=p1)
    CandidateScreeningRecord.objects.create(
        application=app1,
        job=active_job,
        structured_resume={
            "candidate_name": "Alex Rivera",
            "skills": ["Python", "Django", "React", "PostgreSQL", "Docker"],
            "experience": [
                {"company": "TechCorp", "title": "Staff Engineer", "description": "Led backend architecture."}
            ],
        },
        criteria_evaluations={
            "experience": {"score": 95, "reason": "9 years lead full stack experience."},
            "skills": {"score": 90, "reason": "Mastery of Python & React."},
        },
    )

    # Candidate 2: Marcus Johnson
    u2 = User.objects.create_user(email="marcus@example.com", password="pwd", name="Marcus Johnson")
    p2 = SeekerProfile.objects.create(user=u2)
    app2 = Application.objects.create(job=active_job, seeker=p2)
    CandidateScreeningRecord.objects.create(
        application=app2,
        job=active_job,
        structured_resume={
            "candidate_name": "Marcus Johnson",
            "skills": ["React", "TypeScript", "Python", "GraphQL"],
            "experience": [
                {"company": "FintechInc", "title": "Senior Frontend Dev", "description": "Built React dashboards."}
            ],
        },
        criteria_evaluations={
            "experience": {"score": 85, "reason": "7 years front-heavy engineering."},
            "skills": {"score": 92, "reason": "High React & TypeScript proficiency."},
        },
    )

    # Ranking snapshot
    JobRankingSnapshot.objects.create(
        job=active_job,
        total_candidates=2,
        weights_used={"experience": 0.4, "skills": 0.3, "projects": 0.2, "education": 0.1},
        ranked_candidates=[
            {
                "rank": 1,
                "application_id": app1.id,
                "candidate_id": p1.id,
                "candidate_name": "Alex Rivera",
                "candidate_email": "alex@example.com",
                "criteria_scores": {"experience": 95, "skills": 90},
                "criteria_details": {
                    "experience": {"score": 95, "reason": "9 years lead full stack experience."},
                    "skills": {"score": 90, "reason": "Mastery of Python & React."},
                },
                "final_score": 92.5,
            },
            {
                "rank": 2,
                "application_id": app2.id,
                "candidate_id": p2.id,
                "candidate_name": "Marcus Johnson",
                "candidate_email": "marcus@example.com",
                "criteria_scores": {"experience": 85, "skills": 92},
                "criteria_details": {
                    "experience": {"score": 85, "reason": "7 years front-heavy engineering."},
                    "skills": {"score": 92, "reason": "High React & TypeScript proficiency."},
                },
                "final_score": 88.0,
            },
        ],
    )
    return [app1, app2]


# ── 1. Unit Tests for Copilot Service ────────────────────────────────────


class TestCopilotService:
    def test_build_recruiter_agent_context(self, active_job, seeded_candidates):
        context = build_recruiter_agent_context(active_job)
        assert context["job_title"] == "Senior Python & React Engineer"
        assert context["total_ranked"] == 2
        assert len(context["candidates"]) == 2
        assert context["candidates"][0]["name"] == "Alex Rivera"
        assert context["candidates"][0]["final_score"] == 92.5
        assert "Python" in context["candidates"][0]["skills"]

    @patch("talentwright.resume_screening.services.copilot.get_llm_provider")
    def test_execute_copilot_command_with_llm(self, mock_get_provider, active_job, seeded_candidates):
        mock_provider = MagicMock()
        mock_provider.generate_chat_response.return_value = (
            "### Candidate Comparison\n"
            "Alex Rivera is the best overall fit with 92.5% match.\n"
            "I recommend we shortlist Alex Rivera for an initial interview."
        )
        mock_get_provider.return_value = mock_provider

        response = execute_copilot_command(
            job=active_job,
            message="Compare top 2 candidates and give a recommendation",
            history=[CopilotMessage(role="user", content="Hello")],
        )

        assert "Alex Rivera" in response.reply
        assert len(response.suggested_actions) >= 1
        assert response.suggested_actions[0].action_type == "shortlist"
        assert response.suggested_actions[0].candidate_name == "Alex Rivera"

    @patch("talentwright.resume_screening.services.copilot.get_llm_provider")
    def test_execute_copilot_command_fallback_on_error(self, mock_get_provider, active_job, seeded_candidates):
        mock_provider = MagicMock()
        mock_provider.generate_chat_response.side_effect = LLMProviderError("API rate limit exceeded")
        mock_get_provider.return_value = mock_provider

        response = execute_copilot_command(
            job=active_job,
            message="Compare top 2 candidates",
        )

        # Fallback should produce structured comparison
        assert "Comparative Evaluation" in response.reply
        assert "Alex Rivera" in response.reply
        assert "Marcus Johnson" in response.reply
        assert len(response.suggested_actions) >= 1


# ── 2. Integration Tests for Copilot API Endpoint ───────────────────────


class TestCopilotEndpoint:
    def test_unauthenticated_request_rejected(self, active_job):
        client = APIClient()
        url = f"/api/screening/jobs/{active_job.id}/copilot/"
        response = client.post(url, {"message": "Hello"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jobseeker_rejected(self, seeker_user, active_job):
        client = APIClient()
        client.force_authenticate(user=seeker_user)
        url = f"/api/screening/jobs/{active_job.id}/copilot/"
        response = client.post(url, {"message": "Hello"}, format="json")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_other_employer_cannot_access(self, other_employer_user, active_job):
        client = APIClient()
        client.force_authenticate(user=other_employer_user)
        url = f"/api/screening/jobs/{active_job.id}/copilot/"
        response = client.post(url, {"message": "Hello"}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @patch("talentwright.resume_screening.services.copilot.get_llm_provider")
    def test_employer_successful_copilot_call(self, mock_get_provider, employer_user, active_job, seeded_candidates):
        mock_provider = MagicMock()
        mock_provider.generate_chat_response.return_value = (
            "### Tailored Interview Questions for Alex Rivera\n"
            "1. Describe your experience scaling Python backend APIs.\n"
            "2. How do you test full-stack applications?"
        )
        mock_get_provider.return_value = mock_provider

        client = APIClient()
        client.force_authenticate(user=employer_user)
        url = f"/api/screening/jobs/{active_job.id}/copilot/"
        response = client.post(
            url,
            {
                "message": "Generate interview questions for Alex Rivera",
                "history": [],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "reply" in data
        assert "Interview Questions" in data["reply"]
        assert "suggested_actions" in data
