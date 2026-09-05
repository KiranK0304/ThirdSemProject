"""Schemas and type definitions for objective resume baseline evaluation."""

from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel
from pydantic import Field


class JobContext(TypedDict, total=False):
    """Internal lightweight container for job and application data.

    Uses TypedDict for zero runtime validation overhead.
    """

    job_id: int
    title: str
    description: str
    cover_letter: str


class CriterionEvaluation(BaseModel):
    """Evaluation of a specific baseline dimension (e.g. skills, experience, education)."""

    score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Objective score from 0.0 to 100.0",
    )
    reasoning: str = Field(
        default="",
        description="Clear, factual justification for the score based strictly on resume evidence",
    )
    matched_evidence: list[str] = Field(
        default_factory=list,
        description="List of specific skills, technologies, or achievements matched in the resume",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description="List of required or desired job qualifications missing from the resume",
    )


class EvaluationScorecard(BaseModel):
    """Complete baseline scorecard evaluating candidate against job criteria."""

    overall_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Synthesized baseline score from 0.0 to 100.0",
    )
    recommendation: str = Field(
        default="MODERATE_FIT",
        description="Recommendation category: 'STRONG_FIT', 'MODERATE_FIT', or 'WEAK_FIT'",
    )
    skills_evaluation: CriterionEvaluation = Field(
        default_factory=CriterionEvaluation,
        description="Evaluation of candidate technical and professional skills vs requirements",
    )
    experience_evaluation: CriterionEvaluation = Field(
        default_factory=CriterionEvaluation,
        description="Evaluation of years, relevance, and depth of work experience",
    )
    education_evaluation: CriterionEvaluation = Field(
        default_factory=CriterionEvaluation,
        description="Evaluation of degree, certifications, and educational background",
    )
    summary: str = Field(
        default="",
        description="Concise 2-3 sentence executive summary of candidate qualification",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Top 2-4 candidate strengths relative to the role",
    )
    concerns: list[str] = Field(
        default_factory=list,
        description="Identified gaps, missing requirements, or areas of potential concern",
    )
