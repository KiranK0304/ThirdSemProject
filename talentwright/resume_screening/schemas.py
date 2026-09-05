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
