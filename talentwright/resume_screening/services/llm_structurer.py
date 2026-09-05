"""Resume structuring service using LLM.

Takes raw resume text and produces a StructuredResume by sending the
text through an LLM with a predefined Pydantic schema.
"""
from __future__ import annotations

import json
import logging

from talentwright.resume_screening.prompts import build_resume_structuring_prompt
from talentwright.resume_screening.schemas import StructuredResume
from talentwright.resume_screening.services.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


def structure_resume(raw_text: str) -> StructuredResume:
    """Convert raw resume text into structured data using the LLM.

    Builds a prompt that includes the Pydantic JSON schema, sends it
    to the configured LLM provider, and returns the validated result.

    Args:
        raw_text: The raw text extracted from a resume PDF.

    Returns:
        StructuredResume populated with information from the resume.

    Raises:
        LLMProviderError: If the LLM call or response parsing fails.
    """
    schema_json = json.dumps(
        StructuredResume.model_json_schema(),
        indent=2,
    )
    prompt = build_resume_structuring_prompt(
        resume_text=raw_text,
        schema_json=schema_json,
    )

    provider = get_llm_provider()
    result = provider.generate_structured(
        prompt=prompt,
        response_schema=StructuredResume,
        temperature=0.0,
    )

    logger.info(
        "Resume structured: name=%s, skills=%d, experience=%d, education=%d",
        result.candidate_name,
        len(result.skills),
        len(result.experience),
        len(result.education),
    )

    return result
