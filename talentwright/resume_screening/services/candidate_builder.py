"""Candidate data builder service.

Combines structured resume data with application information from the
database to create a complete CandidateScreeningData record.
"""
from __future__ import annotations

import logging

from talentwright.applications.models import Application
from talentwright.resume_screening.schemas import ApplicationInfo
from talentwright.resume_screening.schemas import CandidateScreeningData
from talentwright.resume_screening.schemas import ProcessingStatus
from talentwright.resume_screening.schemas import StructuredResume

logger = logging.getLogger(__name__)


def build_application_info(application: Application) -> ApplicationInfo:
    """Extract application-level information from a database record.

    Args:
        application: An Application model instance with ``seeker``,
            ``seeker__user``, and ``job`` relations pre-fetched.

    Returns:
        ApplicationInfo populated from the database.
    """
    return ApplicationInfo(
        application_id=application.id,
        job_id=application.job_id,
        job_title=application.job.title,
        candidate_id=application.seeker_id,
        user_id=application.seeker.user_id,
        candidate_name=application.seeker.user.name or application.seeker.user.email,
        candidate_email=application.seeker.user.email,
        cover_letter=application.cover_letter or "",
        application_status=application.status,
        applied_at=application.created_at.isoformat(),
    )


def build_candidate_data(
    application: Application,
    structured_resume: StructuredResume | None,
    processing: ProcessingStatus,
) -> CandidateScreeningData:
    """Build a complete candidate screening record.

    Combines database application info with LLM-structured resume data
    and processing status into one CandidateScreeningData object ready
    for future ranking.

    Args:
        application: The Application model instance.
        structured_resume: LLM-structured resume, or None on failure.
        processing: Status tracking for this candidate's processing.

    Returns:
        Complete CandidateScreeningData.
    """
    return CandidateScreeningData(
        application=build_application_info(application),
        resume=structured_resume,
        processing=processing,
    )
