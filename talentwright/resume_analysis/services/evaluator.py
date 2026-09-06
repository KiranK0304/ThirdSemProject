"""Objective baseline evaluation service comparing structured resumes to job requirements."""

from __future__ import annotations

import json
import logging

from talentwright.resume_analysis.evaluation_schemas import EvaluationScorecard
from talentwright.resume_analysis.evaluation_schemas import JobContext
from talentwright.resume_analysis.schemas import StructuredResume
from talentwright.resume_analysis.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

EVALUATOR_SYSTEM_PROMPT = (
    "You are an objective, calibrated technical recruitment evaluator.\n"
    "Your objective is to evaluate a candidate's structured resume against a specific "
    "job description and baseline requirements.\n\n"
    "Evaluation Rules:\n"
    "1. Strict Objectivity: Base every score and reasoning strictly on concrete facts and evidence in the resume.\n"
    "2. No Hallucinations: If a candidate does not explicitly list a required qualification, treat it as missing (gap).\n"
    "3. Dimensional Scoring (0.0 to 100.0):\n"
    "   - skills_evaluation (Weight: 50%): Technical skills match against required and preferred technologies.\n"
    "   - experience_evaluation (Weight: 35%): Total years, seniority, and domain relevance relative to the role.\n"
    "   - education_evaluation (Weight: 15%): Educational pedigree, degree relevance, and certifications.\n"
    "   - overall_score: Weighted composite score computed as:\n"
    "     (skills_score * 0.50) + (experience_score * 0.35) + (education_score * 0.15)\n"
    "4. Recommendation:\n"
    "   - 'STRONG_FIT': overall_score >= 75.0\n"
    "   - 'MODERATE_FIT': 50.0 <= overall_score < 75.0\n"
    "   - 'WEAK_FIT': overall_score < 50.0\n"
    "5. Output must strictly adhere to the requested JSON schema."
)

EVALUATOR_USER_PROMPT_TEMPLATE = """Evaluate the candidate's structured resume against the job requirements below.

### Target Job Context:
- **Title**: {job_title}
- **Description & Requirements**:
{job_description}
{cover_letter_section}

### Candidate Structured Resume:
{resume_json}

### Target Output JSON Schema:
{schema_json}

Provide a comprehensive, objective baseline evaluation formatted strictly as JSON matching the schema above."""


def calculate_composite_score(
    skills_score: float,
    experience_score: float,
    education_score: float,
) -> tuple[float, str]:
    """Calculate deterministic composite overall score and recommendation tier.

    Weights:
        - Skills: 50%
        - Experience: 35%
        - Education: 15%
    """
    composite = round(
        (skills_score * 0.50) + (experience_score * 0.35) + (education_score * 0.15),
        2,
    )
    clamped_score = max(0.0, min(composite, 100.0))

    if clamped_score >= 75.0:
        recommendation = "STRONG_FIT"
    elif clamped_score >= 50.0:
        recommendation = "MODERATE_FIT"
    else:
        recommendation = "WEAK_FIT"

    return clamped_score, recommendation


def evaluate_resume(
    resume: StructuredResume,
    job_context: JobContext,
    llm_client: LLMClient | None = None,
) -> EvaluationScorecard:
    """Evaluate a StructuredResume against a JobContext using the LLM.

    Args:
        resume: The structured candidate resume data.
        job_context: Lightweight TypedDict containing job title, description, and optional cover letter.
        llm_client: Optional LLMClient instance (initialized if not passed).

    Returns:
        EvaluationScorecard: Validated scorecard containing dimensional scores and evidence.

    Raises:
        ValueError: If job title or description is missing.
        ResumeParsingError: If LLM evaluation fails.
    """
    job_title = job_context.get("title", "").strip()
    job_description = job_context.get("description", "").strip()

    if not job_title and not job_description:
        msg = "JobContext must contain at least a title or description for evaluation."
        raise ValueError(msg)

    cover_letter = job_context.get("cover_letter", "").strip()
    cover_letter_section = (
        f"\n### Candidate Cover Letter:\n{cover_letter}\n" if cover_letter else ""
    )

    if llm_client is None:
        llm_client = LLMClient()

    resume_json = json.dumps(resume.model_dump(), separators=(",", ":"))
    schema_json = json.dumps(EvaluationScorecard.model_json_schema(), separators=(",", ":"))

    prompt = EVALUATOR_USER_PROMPT_TEMPLATE.format(
        job_title=job_title or "Not specified",
        job_description=job_description or "Not specified",
        cover_letter_section=cover_letter_section,
        resume_json=resume_json,
        schema_json=schema_json,
    )

    logger.info("Evaluating candidate resume for job '%s'", job_title)
    scorecard = llm_client.generate_structured(
        prompt=prompt,
        system_prompt=EVALUATOR_SYSTEM_PROMPT,
        response_model=EvaluationScorecard,
        temperature=0.0,
    )

    # Deterministically calculate composite overall_score and recommendation
    # based on explicit dimension weights (50% skills, 35% experience, 15% education)
    computed_score, computed_rec = calculate_composite_score(
        skills_score=scorecard.skills_evaluation.score,
        experience_score=scorecard.experience_evaluation.score,
        education_score=scorecard.education_evaluation.score,
    )
    scorecard.overall_score = computed_score
    scorecard.recommendation = computed_rec

    return scorecard
