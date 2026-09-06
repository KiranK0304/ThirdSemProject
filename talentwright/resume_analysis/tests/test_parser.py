"""Tests for LLM client and resume parser service."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from talentwright.resume_analysis.exceptions import EmptyResumeError
from talentwright.resume_analysis.exceptions import LLMConfigurationError
from talentwright.resume_analysis.exceptions import ResumeParsingError
from talentwright.resume_analysis.schemas import StructuredResume
from talentwright.resume_analysis.services.llm_client import LLMClient
from talentwright.resume_analysis.services.parser import parse_resume_text


class DummyChoice:
    def __init__(self, content: str):
        self.message = MagicMock(content=content)


class DummyResponse:
    def __init__(self, content: str):
        self.choices = [DummyChoice(content)]


def test_llm_client_missing_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("SCREENING_LLM_API_KEY", raising=False)
    with patch(
        "talentwright.resume_analysis.services.llm_client._get_setting", return_value=""
    ):
        with pytest.raises(
            LLMConfigurationError, match="Neither OPENROUTER_API_KEY nor"
        ):
            LLMClient(api_key=None)


def test_llm_client_clean_json_response():
    client = LLMClient(api_key="test-key")

    raw_markdown = '```json\n{"summary": "Test engineer", "skills": ["Python"]}\n```'
    cleaned = client._clean_json_response(raw_markdown)
    assert cleaned == '{"summary": "Test engineer", "skills": ["Python"]}'

    raw_plain = '{"summary": "Test engineer", "skills": ["Python"]}'
    assert client._clean_json_response(raw_plain) == raw_plain


def test_llm_client_generate_structured_success():
    client = LLMClient(api_key="test-key")
    json_payload = '{"summary": "Software Engineer", "skills": ["Python", "Docker"], "total_years_experience": 3.0}'

    with patch.object(
        client.client.chat.completions,
        "create",
        return_value=DummyResponse(json_payload),
    ):
        result = client.generate_structured(
            prompt="parse this",
            system_prompt="system instructions",
            response_model=StructuredResume,
        )
        assert isinstance(result, StructuredResume)
        assert result.summary == "Software Engineer"
        assert result.skills == ["Python", "Docker"]
        assert result.total_years_experience == 3.0


def test_llm_client_empty_response():
    client = LLMClient(api_key="test-key")
    with (
        patch.object(
            client.client.chat.completions,
            "create",
            return_value=DummyResponse(""),
        ),
        pytest.raises(ResumeParsingError, match="LLM returned an empty response"),
    ):
        client.generate_structured(
            prompt="parse this",
            system_prompt="system",
            response_model=StructuredResume,
        )


def test_llm_client_invalid_json():
    client = LLMClient(api_key="test-key")
    with (
        patch.object(
            client.client.chat.completions,
            "create",
            return_value=DummyResponse("Not a valid JSON payload"),
        ),
        pytest.raises(ResumeParsingError, match="Failed to validate LLM response"),
    ):
        client.generate_structured(
            prompt="parse this",
            system_prompt="system",
            response_model=StructuredResume,
        )


def test_llm_client_api_failure():
    client = LLMClient(api_key="test-key")
    with (
        patch.object(
            client.client.chat.completions,
            "create",
            side_effect=RuntimeError("Connection refused"),
        ),
        pytest.raises(ResumeParsingError, match="LLM API request failed"),
    ):
        client.generate_structured(
            prompt="parse this",
            system_prompt="system",
            response_model=StructuredResume,
        )


def test_parse_resume_text_empty_or_short():
    with pytest.raises(EmptyResumeError):
        parse_resume_text("")

    with pytest.raises(EmptyResumeError):
        parse_resume_text("   short   ")


def test_parse_resume_text_success_with_mock_client():
    mock_client = MagicMock(spec=LLMClient)
    expected_resume = StructuredResume(
        summary="Senior Backend Developer",
        skills=["Python", "Django", "PostgreSQL"],
        total_years_experience=5.0,
    )
    mock_client.generate_structured.return_value = expected_resume

    sample_text = "Jane Doe\nEmail: jane@example.com\nSenior Backend Developer with 5 years experience in Python and Django."
    result = parse_resume_text(sample_text, llm_client=mock_client)

    assert result == expected_resume
    mock_client.generate_structured.assert_called_once()
    call_args = mock_client.generate_structured.call_args
    assert "Target JSON Schema:" in call_args.kwargs["prompt"]
    assert sample_text in call_args.kwargs["prompt"]
