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


# ── Candidate Evaluation Prompt ─────────────────────────────────────────

CANDIDATE_EVALUATION_PROMPT = """\
You are an expert, objective technical recruiter and hiring evaluator.

Your task is to evaluate ONE candidate for the following job, based strictly on the provided job description and the candidate's screening data.

JOB DETAILS:
Title: {job_title}
Description & Requirements:
{job_description}

CANDIDATE SCREENING DATA:
Candidate Name: {candidate_name}
Candidate Email: {candidate_email}
Cover Letter:
{cover_letter}

Structured Resume Data:
{resume_json}

EVALUATION CRITERIA TO SCORE:
Please evaluate the candidate on each of the following criteria:
{criteria_list}

RULES:
1. Evaluate ONLY this single candidate independently against the job requirements.
2. For every criterion listed above, assign an integer score from 0 to 100:
   - 90-100: Exceptional match; exceeds the requirements for this criterion.
   - 75-89: Strong match; meets core requirements well.
   - 60-74: Moderate match; meets some requirements but has noticeable gaps.
   - 40-59: Weak match; limited relevance or significant gaps.
   - 0-39: Poor or no match; lacks required qualifications or no information provided.
3. For each criterion, provide a concise explanation (1-3 sentences) citing concrete evidence from the candidate's resume/cover letter.
4. Do NOT calculate any overall, weighted, or composite score. Return ONLY individual criterion scores.
5. Base your evaluation strictly on the provided information. Do not invent or assume details.

JSON Schema:
{schema}

Respond with ONLY a valid JSON object matching the schema above.
"""


def build_candidate_evaluation_prompt(
    job_title: str,
    job_description: str,
    candidate_name: str,
    candidate_email: str,
    cover_letter: str,
    resume_json: str,
    criteria: list[str],
    schema_json: str,
) -> str:
    """Build the prompt for evaluating a single candidate against criteria."""
    criteria_formatted = "\n".join(f"- {c}" for c in criteria)
    return CANDIDATE_EVALUATION_PROMPT.format(
        job_title=job_title,
        job_description=job_description,
        candidate_name=candidate_name,
        candidate_email=candidate_email,
        cover_letter=cover_letter or "None provided.",
        resume_json=resume_json,
        criteria_list=criteria_formatted,
        schema=schema_json,
    )

