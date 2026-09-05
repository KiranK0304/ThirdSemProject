"""Pydantic schemas for structured resume data."""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class CandidateContact(BaseModel):
    """Extracted contact information of the candidate."""

    name: str = Field(default="", description="Full name of the candidate")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    location: str = Field(default="", description="City, State / Country or current location")
    linkedin_url: str = Field(default="", description="LinkedIn profile URL")
    github_url: str = Field(default="", description="GitHub profile URL")
    portfolio_url: str = Field(default="", description="Personal website or portfolio URL")


class WorkExperience(BaseModel):
    """Work experience entry."""

    company: str = Field(default="", description="Company or organization name")
    title: str = Field(default="", description="Job title or role")
    start_date: str = Field(default="", description="Start date (e.g., 'Jan 2021' or '2021-01')")
    end_date: str = Field(default="", description="End date (e.g., 'Present', 'Dec 2023')")
    is_current: bool = Field(default=False, description="Whether the candidate currently works here")
    description: str = Field(default="", description="Summary of responsibilities and achievements")
    technologies: list[str] = Field(
        default_factory=list,
        description="Tools, frameworks, and technologies used in this role",
    )


class Education(BaseModel):
    """Education history entry."""

    institution: str = Field(default="", description="College, university, or school name")
    degree: str = Field(default="", description="Degree obtained (e.g., B.S., M.S., Ph.D., Diploma)")
    field_of_study: str = Field(default="", description="Major or field of study (e.g., Computer Science)")
    graduation_year: str = Field(default="", description="Year of graduation or expected graduation")
    gpa: str = Field(default="", description="GPA or honors if mentioned")


class ProjectItem(BaseModel):
    """Personal or professional project entry."""

    title: str = Field(default="", description="Project title or name")
    description: str = Field(default="", description="Brief description of the project and impact")
    technologies: list[str] = Field(
        default_factory=list,
        description="Technologies and languages used in the project",
    )
    link: str = Field(default="", description="Repository or live URL if mentioned")


class Certification(BaseModel):
    """Certification or license entry."""

    name: str = Field(default="", description="Certification title or name")
    issuer: str = Field(default="", description="Issuing organization or authority")
    issue_date: str = Field(default="", description="Date issued or valid through")


class StructuredResume(BaseModel):
    """Complete structured representation of a parsed resume."""

    contact: CandidateContact = Field(
        default_factory=CandidateContact,
        description="Contact information",
    )
    summary: str = Field(
        default="",
        description="Professional summary or objective statement",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Normalized list of hard and technical skills mentioned in the resume",
    )
    total_years_experience: float = Field(
        default=0.0,
        description="Estimated total professional experience in years",
    )
    work_experience: list[WorkExperience] = Field(
        default_factory=list,
        description="List of work experience entries in reverse chronological order",
    )
    education: list[Education] = Field(
        default_factory=list,
        description="List of educational qualifications",
    )
    projects: list[ProjectItem] = Field(
        default_factory=list,
        description="Projects highlighted on the resume",
    )
    certifications: list[Certification] = Field(
        default_factory=list,
        description="Certifications or licenses",
    )
