"""LLM prompt templates for resume screening.

Prompts are separated from business logic so they can be edited,
versioned, or A/B tested without touching service code.
"""

RESUME_STRUCTURING_PROMPT = """\
You are a precise resume information extractor.

Given the raw text of a resume, extract and structure the information
into a JSON object matching the schema below.

Rules:
- Extract ONLY information that is explicitly present in the resume.
- Do NOT invent, infer, or hallucinate any information.
- If a section has no relevant content in the resume, use null for
  optional fields and empty arrays for list fields.
- For skills, list each distinct skill as a separate string.
- For dates, use the exact format found in the resume (e.g., "Jan 2022",
  "2022", "01/2022"). Do not convert to any standard format.
- For work experience entries, include key responsibilities and
  achievements in the description field.
- For technologies, list specific tools, frameworks, and languages used.
- Place any information that doesn't fit the defined categories into
  the additional_info array as descriptive strings.

JSON Schema:
{schema}

Resume text:
---
{resume_text}
---

Respond with ONLY a valid JSON object matching the schema above.
"""


def build_resume_structuring_prompt(resume_text: str, schema_json: str) -> str:
    """Build the complete prompt for resume structuring.

    Args:
        resume_text: Raw text extracted from the resume PDF.
        schema_json: JSON string of the StructuredResume schema.

    Returns:
        Formatted prompt string ready to send to the LLM.
    """
    return RESUME_STRUCTURING_PROMPT.format(
        resume_text=resume_text,
        schema=schema_json,
    )
