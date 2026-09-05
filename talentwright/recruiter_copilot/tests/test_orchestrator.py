"""Tests for the CopilotOrchestrator engine."""

import json
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.recruiter_copilot.models import CopilotMessage
from talentwright.recruiter_copilot.models import CopilotSession
from talentwright.recruiter_copilot.models import MessageRole
from talentwright.recruiter_copilot.orchestrator.engine import CopilotOrchestrator
from talentwright.recruiter_copilot.tools.registry import ToolRegistry
from talentwright.resume_analysis.services.llm_client import LLMClient
from talentwright.users.models import EmployerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


class DummyFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class DummyToolCall:
    def __init__(self, call_id: str, name: str, arguments: str):
        self.id = call_id
        self.function = DummyFunction(name, arguments)


class DummyMessage:
    def __init__(self, content: str | None = None, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls


class DummyChoice:
    def __init__(self, message: DummyMessage):
        self.message = message


class DummyResponse:
    def __init__(self, message: DummyMessage):
        self.choices = [DummyChoice(message)]


@pytest.fixture
def copilot_session(db):
    employer_user = User.objects.create_user(
        email="orch_emp@example.com", password="Password123!"
    )
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    job = Job.objects.create(
        employer=employer,
        title="Staff Data Engineer",
        description="Looking for Spark, Snowflake, and Python.",
        status=JobStatus.OPEN,
    )
    return CopilotSession.objects.create(
        job=job, employer=employer, title="Data Eng Search"
    )


@pytest.mark.django_db
def test_orchestrator_direct_conversational_reply(copilot_session):
    mock_llm = MagicMock()
    mock_llm.model = "test-model"

    direct_msg = DummyMessage(
        content="The job requires 5+ years of Spark and Python.", tool_calls=None
    )
    mock_llm.client.chat.completions.create.return_value = DummyResponse(direct_msg)

    orchestrator = CopilotOrchestrator(llm_client=mock_llm)
    reply, metadata = orchestrator.run(
        copilot_session, "What are the job requirements?"
    )

    assert reply == "The job requires 5+ years of Spark and Python."
    assert metadata["tools_called"] == []
    mock_llm.client.chat.completions.create.assert_called_once()


@pytest.mark.django_db
def test_orchestrator_executes_tool_call_flow(copilot_session):
    mock_llm = MagicMock()
    mock_llm.model = "test-model"

    # 1. First LLM response requests a tool call: get_top_candidates(limit=2)
    tool_call = DummyToolCall(
        call_id="call_abc", name="get_top_candidates", arguments='{"limit": 2}'
    )
    first_msg = DummyMessage(content=None, tool_calls=[tool_call])

    # 2. Second LLM response provides conversational summary after tool results
    second_msg = DummyMessage(
        content="Here are the top candidates: Alice is ranked #1.",
        tool_calls=None,
    )

    mock_llm.client.chat.completions.create.side_effect = [
        DummyResponse(first_msg),
        DummyResponse(second_msg),
    ]

    # Mock tool registry
    mock_registry = MagicMock(spec=ToolRegistry)
    mock_registry.get_definitions.return_value = [{"type": "function"}]
    mock_candidates = [
        {"application_id": 1, "name": "Alice", "score": 95.0},
        {"application_id": 2, "name": "Bob", "score": 88.0},
    ]
    mock_registry.execute.return_value = mock_candidates

    orchestrator = CopilotOrchestrator(llm_client=mock_llm, registry=mock_registry)
    reply, metadata = orchestrator.run(copilot_session, "Who are the top candidates?")

    assert reply == "Here are the top candidates: Alice is ranked #1."
    assert len(metadata["tools_called"]) == 1
    assert metadata["tools_called"][0]["name"] == "get_top_candidates"
    assert metadata["candidates"] == mock_candidates

    # Verify tool execution
    mock_registry.execute.assert_called_once_with(
        tool_name="get_top_candidates",
        arguments={"limit": 2},
        context={"job_id": copilot_session.job_id},
    )
    assert mock_llm.client.chat.completions.create.call_count == 2


@pytest.mark.django_db
def test_orchestrator_handles_exception_gracefully(copilot_session):
    mock_llm = MagicMock()
    mock_llm.model = "test-model"
    mock_llm.client.chat.completions.create.side_effect = RuntimeError(
        "API connection timeout"
    )

    orchestrator = CopilotOrchestrator(llm_client=mock_llm)
    reply, metadata = orchestrator.run(copilot_session, "Hello")

    assert "I apologize" in reply
    assert "error" in metadata
