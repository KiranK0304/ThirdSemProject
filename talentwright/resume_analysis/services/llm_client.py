"""LLM client for resume analysis via OpenAI/OpenRouter."""

from __future__ import annotations

import logging
import os
import re
from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from talentwright.resume_analysis.exceptions import LLMConfigurationError
from talentwright.resume_analysis.exceptions import ResumeParsingError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def _get_setting(name: str, default: str = "") -> str:
    """Fetch setting from Django settings or environment variables."""
    try:
        from django.conf import settings as django_settings

        value = getattr(django_settings, name, None)
        if value:
            return str(value)
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get(name, default)


class LLMClient:
    """Client for generating structured responses using an OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = (
            api_key
            or _get_setting("SCREENING_LLM_API_KEY")
            or _get_setting("OPENROUTER_API_KEY")
            or _get_setting("OPENAI_API_KEY")
        )
        if not self.api_key:
            msg = "Neither OPENROUTER_API_KEY nor SCREENING_LLM_API_KEY nor OPENAI_API_KEY is configured."
            raise LLMConfigurationError(msg)

        default_base_url = (
            "https://api.openai.com/v1"
            if _get_setting("OPENAI_API_KEY")
            and not (_get_setting("SCREENING_LLM_BASE_URL") or _get_setting("OPENROUTER_API_KEY") or _get_setting("SCREENING_LLM_API_KEY"))
            else "https://openrouter.ai/api/v1"
        )
        self.base_url = (
            base_url
            or _get_setting("SCREENING_LLM_BASE_URL")
            or default_base_url
        )
        self.model = (
            model or _get_setting("SCREENING_LLM_MODEL") or "openai/gpt-4o-mini"
        )
        self.timeout = timeout
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def _clean_json_response(self, text: str) -> str:
        """Strip markdown code fence blocks if returned by the LLM."""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_model: type[T],
        temperature: float = 0.0,
    ) -> T:
        """Query LLM and parse the returned JSON into the specified Pydantic model."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=2500,
            )
        except Exception as exc:
            logger.exception("LLM API call failed")
            raise ResumeParsingError(f"LLM API request failed: {exc}") from exc

        content = response.choices[0].message.content
        if not content:
            raise ResumeParsingError("LLM returned an empty response.")

        cleaned = self._clean_json_response(content)

        try:
            return response_model.model_validate_json(cleaned)
        except Exception as exc:
            logger.exception("Failed to validate JSON into %s", response_model.__name__)
            raise ResumeParsingError(
                f"Failed to validate LLM response against {response_model.__name__}: {exc}",
            ) from exc
