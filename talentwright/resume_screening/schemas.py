"""Pydantic schemas for resume screening data structures.

These schemas serve as:
1. The predefined structure that the LLM fills from extracted PDF text.
2. Internal pipeline data types for passing data between stages.
3. API response serialization.
"""
from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


# ── Resume Structuring Schema (LLM output) ──────────────────────────────


class ContactInfo(BaseModel):
    """Contact details extracted from resume."""

    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None


class WorkExperience(BaseModel):
    """A single work experience entry."""

    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


class Education(BaseModel):
    """A single education entry."""

    institution: str
    degree: str
    start_date: str | None = None
    end_date: str | None = None
    details: str | None = None


class Project(BaseModel):
    """A notable project."""

    name: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None


class Certification(BaseModel):
    """A professional certification."""

    name: str
    issuer: str | None = None
    date: str | None = None


class StructuredResume(BaseModel):
    """Complete structured representation of a resume.

    This schema is intentionally generic — it captures common resume
    sections without domain-specific categories.  The LLM populates
    what exists in the resume; missing sections remain as defaults.
    """

    candidate_name: str | None = None
    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    professional_summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    additional_info: list[str] = Field(default_factory=list)


# ── Application Info Schema (from database) ─────────────────────────────


class ApplicationInfo(BaseModel):
    """Application-level data pulled from the database."""

    application_id: int
    job_id: int
    job_title: str
    candidate_id: int
    user_id: int
    candidate_name: str
    candidate_email: str
    cover_letter: str
    application_status: str
    applied_at: str


# ── Processing Status Schema ────────────────────────────────────────────


class ProcessingStatus(BaseModel):
    """Tracks what happened during processing of a single candidate."""

    success: bool
    has_resume: bool
    resume_extracted: bool
    resume_structured: bool
    errors: list[str] = Field(default_factory=list)


# ── Candidate Screening Data Schema ─────────────────────────────────────


class CandidateScreeningData(BaseModel):
    """One complete candidate record — ready for future ranking."""

    application: ApplicationInfo
    resume: StructuredResume | None = None
    processing: ProcessingStatus


# ── Job Screening Response Schema ───────────────────────────────────────


class JobScreeningResponse(BaseModel):
    """Top-level response for the prepare endpoint."""

    job_id: int
    job_title: str
    total_applications: int
    successfully_processed: int
    failed_processing: int
    candidates: list[CandidateScreeningData]


# ── Scoring Criteria & Weights Schemas ──────────────────────────────────


class JobCriteriaResponse(BaseModel):
    """Current scoring criteria weights for a job."""

    job_id: int
    weights: dict[str, float]
    is_custom: bool
    available_criteria: list[str] = [
        "experience",
        "skills",
        "projects",
        "education",
        "certifications",
    ]


# ── LLM Candidate Evaluation Schemas ───────────────────────────────────


class CriterionEvaluationItem(BaseModel):
    """Evaluation result for one criterion returned by LLM."""

    criterion: str = Field(description="Name of the criterion, e.g. 'experience', 'skills'")
    score: int = Field(ge=0, le=100, description="Score from 0 to 100")
    reason: str = Field(description="Factual evidence and justification for the score")


class CandidateEvaluationResponse(BaseModel):
    """Raw structured output returned by LLM for one candidate."""

    evaluations: list[CriterionEvaluationItem] = Field(default_factory=list)


class CriterionDetail(BaseModel):
    """Score and explanatory evidence for a specific criterion."""

    score: int = Field(ge=0, le=100)
    reason: str


# ── Candidate Ranking Schemas ──────────────────────────────────────────


class RankedCandidate(BaseModel):
    """A candidate evaluated, scored, and assigned a rank position."""

    rank: int = Field(ge=1, description="Ranking position (1 is top candidate)")
    application_id: int
    candidate_id: int
    candidate_name: str
    candidate_email: str
    criteria_scores: dict[str, int] = Field(
        default_factory=dict,
        description="Individual criterion scores from 0 to 100, e.g. {'experience': 85, 'skills': 72}",
    )
    criteria_details: dict[str, CriterionDetail] = Field(
        default_factory=dict,
        description="Detailed evidence and explanation for each criterion",
    )
    final_score: float = Field(
        description="Deterministic backend weighted final score from 0 to 100",
    )


class JobRankingResponse(BaseModel):
    """Top-level response containing ranked candidates for a job."""

    job_id: int
    job_title: str
    weights_used: dict[str, float]
    total_candidates: int
    ranked_candidates: list[RankedCandidate]
    created_at: str | None = None


# ── AI Recruiter Copilot Schemas ─────────────────────────────────────────


class CopilotAction(BaseModel):
    """An actionable button or shortcut returned by the AI Copilot."""

    action_type: str = Field(
        description="Type of action: 'shortlist', 'copy_text', 'filter', or 'inspect'",
    )
    label: str = Field(description="Display label for the action button")
    application_id: int | None = None
    candidate_id: int | None = None
    candidate_name: str | None = None
    payload: str | None = Field(
        default=None,
        description="Optional payload, such as pre-written email body or questions to copy",
    )


class CopilotMessage(BaseModel):
    """Single message in a copilot conversation."""

    role: str = Field(description="'user' or 'assistant'")
    content: str = Field(description="Message body text in markdown")


class CopilotRequest(BaseModel):
    """Request payload for the copilot endpoint."""

    message: str = Field(description="The user's query or command")
    history: list[CopilotMessage] = Field(
        default_factory=list,
        description="Prior conversation history",
    )
    candidate_ids: list[int] = Field(
        default_factory=list,
        description="Optional application IDs or candidate IDs to focus on",
    )


class CopilotResponse(BaseModel):
    """Response returned by the copilot endpoint."""

    reply: str = Field(description="Assistant response in markdown format")
    suggested_actions: list[CopilotAction] = Field(
        default_factory=list,
        description="List of direct actions the user can execute with 1-click",
    )

