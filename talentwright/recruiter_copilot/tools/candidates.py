"""Database tools for querying and retrieving candidate records."""

from __future__ import annotations

import logging
from typing import Any

from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord

logger = logging.getLogger(__name__)


def get_top_candidates(
    job_id: int,
    limit: Any = 5,
) -> list[dict[str, Any]]:
    """Retrieve top-ranked candidates for a job ordered by overall score.

    Args:
        job_id: Primary key of the job posting.
        limit: Maximum number of candidates to return (clamped between 1 and 20).

    Returns:
        A list of structured candidate summaries.
    """
    try:
        raw_limit = int(limit) if limit is not None else 5
    except (ValueError, TypeError):
        raw_limit = 5
    safe_limit = max(1, min(raw_limit, 20))

    records = (
        ResumeAnalysisRecord.objects.filter(
            application__job_id=job_id,
            status=AnalysisStatus.COMPLETED,
        )
        .select_related("application__seeker__user")
        .order_by("-overall_score")[:safe_limit]
    )

    candidates: list[dict[str, Any]] = []
    for record in records:
        user = getattr(record.application.seeker, "user", None)
        name = (
            user.name
            if user and user.name
            else (user.email if user else f"Applicant #{record.application_id}")
        )
        email = user.email if user else ""
        structured = record.structured_resume or {}
        scorecard = record.evaluation_scorecard or {}

        candidates.append(
            {
                "application_id": record.application_id,
                "name": name,
                "email": email,
                "overall_score": (
                    float(record.overall_score)
                    if record.overall_score is not None
                    else 0.0
                ),
                "recommendation": record.recommendation or "N/A",
                "skills": structured.get("skills", []),
                "years_experience": structured.get("total_years_experience", 0.0),
                "summary": (
                    structured.get("summary")
                    or scorecard.get("summary")
                    or "No summary provided."
                ),
                "strengths": scorecard.get("strengths", []),
                "concerns": scorecard.get("concerns", []),
            }
        )

    logger.info(
        "Retrieved %d top candidates for job #%d",
        len(candidates),
        job_id,
    )
    return candidates
