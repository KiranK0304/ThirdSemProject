"""Tests for Recruiter Copilot API endpoints."""

import pytest
from rest_framework.test import APIClient

from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.recruiter_copilot.models import CopilotMessage
from talentwright.recruiter_copilot.models import CopilotSession
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def employer_setup(db):
    user = User.objects.create_user(
        email="employer1@example.com", password="Password123!", name="Employer One"
    )
    employer = EmployerProfile.objects.create(
        user=user,
        company_name="Acme Tech",
        verification_status=VerificationStatus.APPROVED,
    )
    job = Job.objects.create(
        employer=employer,
        title="Senior Python Backend Developer",
        description="Looking for Django and PostgreSQL expertise.",
        status=JobStatus.OPEN,
    )
    return {"user": user, "employer": employer, "job": job}


@pytest.fixture
def other_employer(db):
    user = User.objects.create_user(
        email="other_emp@example.com", password="Password123!", name="Employer Two"
    )
    employer = EmployerProfile.objects.create(
        user=user,
        company_name="Other Corp",
        verification_status=VerificationStatus.APPROVED,
    )
    return {"user": user, "employer": employer}


@pytest.fixture
def seeker_user(db):
    user = User.objects.create_user(
        email="seeker@example.com", password="Password123!", name="Job Seeker"
    )
    SeekerProfile.objects.create(user=user)
    return user


@pytest.mark.django_db
def test_sessions_unauthenticated_blocked(api_client, employer_setup):
    job_id = employer_setup["job"].id
    response = api_client.get(f"/api/copilot/jobs/{job_id}/sessions/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_sessions_seeker_forbidden(api_client, employer_setup, seeker_user):
    api_client.force_authenticate(user=seeker_user)
    job_id = employer_setup["job"].id
    response = api_client.get(f"/api/copilot/jobs/{job_id}/sessions/")
    assert response.status_code == 403
    assert "Only verified employers" in response.data["error"]


@pytest.mark.django_db
def test_sessions_non_owner_employer_forbidden(
    api_client, employer_setup, other_employer
):
    api_client.force_authenticate(user=other_employer["user"])
    job_id = employer_setup["job"].id
    response = api_client.get(f"/api/copilot/jobs/{job_id}/sessions/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_session_create_and_list_success(api_client, employer_setup):
    user = employer_setup["user"]
    job = employer_setup["job"]
    api_client.force_authenticate(user=user)

    # 1. Initially empty
    list_res = api_client.get(f"/api/copilot/jobs/{job.id}/sessions/")
    assert list_res.status_code == 200
    assert list_res.data == []

    # 2. Create session
    create_res = api_client.post(
        f"/api/copilot/jobs/{job.id}/sessions/",
        data={"title": "Reviewing Python Candidates"},
        format="json",
    )
    assert create_res.status_code == 201
    assert create_res.data["title"] == "Reviewing Python Candidates"
    assert create_res.data["job_id"] == job.id
    session_id = create_res.data["id"]

    # 3. List contains newly created session
    list_res2 = api_client.get(f"/api/copilot/jobs/{job.id}/sessions/")
    assert list_res2.status_code == 200
    assert len(list_res2.data) == 1
    assert list_res2.data[0]["id"] == session_id


@pytest.mark.django_db
def test_messages_empty_content_validation(api_client, employer_setup):
    user = employer_setup["user"]
    job = employer_setup["job"]
    employer = employer_setup["employer"]
    session = CopilotSession.objects.create(job=job, employer=employer, title="Chat")

    api_client.force_authenticate(user=user)
    res = api_client.post(
        f"/api/copilot/sessions/{session.id}/messages/",
        data={"message": "   "},
        format="json",
    )
    assert res.status_code == 400
    assert "cannot be empty" in res.data["error"]


@pytest.mark.django_db
def test_message_send_and_history_retrieval(api_client, employer_setup):
    user = employer_setup["user"]
    job = employer_setup["job"]
    employer = employer_setup["employer"]
    session = CopilotSession.objects.create(
        job=job, employer=employer, title="Shortlist Chat"
    )

    api_client.force_authenticate(user=user)

    # 1. Post user message
    post_res = api_client.post(
        f"/api/copilot/sessions/{session.id}/messages/",
        data={"message": "Show me candidates with at least 3 years in Django"},
        format="json",
    )
    assert post_res.status_code == 201
    assert (
        post_res.data["user_message"]["content"]
        == "Show me candidates with at least 3 years in Django"
    )
    assert post_res.data["user_message"]["role"] == "USER"
    assert post_res.data["assistant_message"]["role"] == "ASSISTANT"

    # 2. Retrieve session message history
    history_res = api_client.get(f"/api/copilot/sessions/{session.id}/messages/")
    assert history_res.status_code == 200
    assert len(history_res.data) == 2
    assert history_res.data[0]["role"] == "USER"
    assert history_res.data[1]["role"] == "ASSISTANT"


@pytest.mark.django_db
def test_message_send_returns_orchestrator_candidate_cards(api_client, employer_setup):
    from unittest.mock import patch

    user = employer_setup["user"]
    job = employer_setup["job"]
    employer = employer_setup["employer"]
    session = CopilotSession.objects.create(
        job=job, employer=employer, title="Shortlist Chat"
    )

    api_client.force_authenticate(user=user)

    mock_candidates = [{"application_id": 10, "name": "Alice", "score": 96.0}]
    with patch(
        "talentwright.recruiter_copilot.api.views.CopilotOrchestrator"
    ) as mock_orch_cls:
        mock_orch = mock_orch_cls.return_value
        mock_orch.run.return_value = (
            "Here is Alice, your top candidate.",
            {
                "candidates": mock_candidates,
                "tools_called": [{"name": "get_top_candidates"}],
            },
        )

        post_res = api_client.post(
            f"/api/copilot/sessions/{session.id}/messages/",
            data={"message": "Show me the top candidate"},
            format="json",
        )
        assert post_res.status_code == 201
        assert (
            post_res.data["assistant_message"]["content"]
            == "Here is Alice, your top candidate."
        )
        assert (
            post_res.data["assistant_message"]["metadata"]["candidates"]
            == mock_candidates
        )
