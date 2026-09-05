"""Resume parsing service using LLM to extract structured data."""

from __future__ import annotations

import json
import logging

from talentwright.resume_analysis.exceptions import EmptyResumeError
from talentwright.resume_analysis.schemas import StructuredResume
from talentwright.resume_analysis.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert resume parsing engine. Your objective is to extract factual, "
    "structured candidate data from raw resume text. Adhere strictly to the provided "
    "JSON schema.\n"
    "Guidelines:\n"
    "1. Do not invent or assume information not present in the text.\n"
    "2. If a field or detail is not found, supply an empty string, empty list, or 0.0.\n"
    "3. Extract technical and hard skills into a clean, normalized list of individual skill names.\n"
    "4. Ensure work experiences are in reverse chronological order if dates are determinable.\n"
    "5. Estimate total professional experience in years based on employment duration.\n"
    "6. Output must be valid JSON matching the schema."
)

PARSER_USER_PROMPT_TEMPLATE = """Extract structured candidate information from the resume text below.

Target JSON Schema:
{schema_json}

Resume Text:
----------------------------------------
{resume_text}
----------------------------------------

Return the output as valid JSON conforming strictly to the schema above."""


def parse_resume_text(
    resume_text: str,
    llm_client: LLMClient | None = None,
) -> StructuredResume:
    """Parse raw resume text into a StructuredResume model.

    Args:
        resume_text: Raw plain text extracted from a resume file.
        llm_client: Optional LLMClient instance (initialized if not provided).

    Returns:
        StructuredResume: Validated structured resume data.

    Raises:
        EmptyResumeError: If the resume text is empty or too short.
        ResumeParsingError: If extraction or validation fails.
    """
    if not resume_text or len(resume_text.strip()) < 20:
        raise EmptyResumeError("Resume text is empty or too short to extract meaningful data.")

    if llm_client is None:
        llm_client = LLMClient()

    schema_json = json.dumps(StructuredResume.model_json_schema(), indent=2)
    prompt = PARSER_USER_PROMPT_TEMPLATE.format(
        schema_json=schema_json,
        resume_text=resume_text.strip(),
    )

    logger.info("Sending resume text (%d characters) for LLM parsing", len(resume_text))
    return llm_client.generate_structured(
        prompt=prompt,
        system_prompt=SYSTEM_PROMPT,
        response_model=StructuredResume,
        temperature=0.0,
    )
