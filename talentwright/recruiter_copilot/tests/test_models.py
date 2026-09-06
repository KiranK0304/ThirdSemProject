"""Tests for CopilotSession and CopilotMessage models."""

import pytest

from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.recruiter_copilot.models import CopilotMessage
from talentwright.recruiter_copilot.models import CopilotSession
from talentwright.recruiter_copilot.models import MessageRole
from talentwright.users.models import EmployerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.mark.django_db
def test_copilot_session_and_message_lifecycle():
    user = User.objects.create(email="recruiter_test@example.com", name="Recruiter")
    employer = EmployerProfile.objects.create(
        user=user,
        verification_status=VerificationStatus.APPROVED,
    )
    job = Job.objects.create(
        employer=employer,
        title="Full Stack Developer",
        status=JobStatus.OPEN,
    )

    session = CopilotSession.objects.create(
        job=job,
        employer=employer,
        title="Candidate Q&A",
    )
    assert session.job == job
    assert session.employer == employer
    assert "Candidate Q&A" in str(session)

    # Add messages
    user_msg = CopilotMessage.objects.create(
        session=session,
        role=MessageRole.USER,
        content="Who has React experience?",
    )
    assistant_msg = CopilotMessage.objects.create(
        session=session,
        role=MessageRole.ASSISTANT,
        content="Found 2 candidates with React experience.",
        metadata={"candidate_ids": [1, 2]},
    )

    assert session.messages.count() == 2
    assert user_msg.role == MessageRole.USER
    assert assistant_msg.metadata["candidate_ids"] == [1, 2]
    assert "[USER]" in str(user_msg)
    assert "[ASSISTANT]" in str(assistant_msg)

    # Cascade delete check
    job.delete()
    assert not CopilotSession.objects.filter(id=session.id).exists()
    assert not CopilotMessage.objects.filter(id=user_msg.id).exists()
