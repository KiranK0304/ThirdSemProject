"""Pipeline orchestrator for candidate data preparation.

Coordinates the full screening pipeline for a job:

    Application → Resume File → PDF Extraction
        → LLM Structuring → Candidate Data Building

This is the main entry point called by API views.
"""
from __future__ import annotations

import logging

from talentwright.applications.models import Application
from talentwright.jobs.models import Job
from talentwright.resume_screening.schemas import CandidateScreeningData
from talentwright.resume_screening.schemas import JobScreeningResponse
from talentwright.resume_screening.schemas import ProcessingStatus
from talentwright.resume_screening.schemas import StructuredResume
from talentwright.resume_screening.services.candidate_builder import build_candidate_data
from talentwright.resume_screening.services.llm_provider import LLMProviderError
from talentwright.resume_screening.services.llm_structurer import structure_resume
from talentwright.resume_screening.services.pdf_extractor import extract_text_from_pdf

logger = logging.getLogger(__name__)


def _process_single_application(application: Application) -> CandidateScreeningData:
    """Process one application through the screening pipeline.

    Handles all error cases gracefully — never raises exceptions.
    Returns CandidateScreeningData with appropriate processing status.
    """
    # ── Step 1: Check if resume exists ──────────────────────────────
    if not application.resume:
        return build_candidate_data(
            application=application,
            structured_resume=None,
            processing=ProcessingStatus(
                success=False,
                has_resume=False,
                resume_extracted=False,
                resume_structured=False,
                errors=["No resume attached to this application"],
            ),
        )

    if not application.resume.file:
        return build_candidate_data(
            application=application,
            structured_resume=None,
            processing=ProcessingStatus(
                success=False,
                has_resume=True,
                resume_extracted=False,
                resume_structured=False,
                errors=["Resume record exists but file is missing"],
            ),
        )

    # ── Check if already structured and cached in DB ────────────────
    from talentwright.resume_screening.models import CandidateScreeningRecord

    file_name = getattr(application.resume.file, "name", "")
    existing_record = CandidateScreeningRecord.objects.filter(application=application).first()
    if existing_record and existing_record.structured_resume and existing_record.resume_file_name == file_name:
        try:
            cached_resume = StructuredResume.model_validate(existing_record.structured_resume)
            return build_candidate_data(
                application=application,
                structured_resume=cached_resume,
                processing=ProcessingStatus(
                    success=True,
                    has_resume=True,
                    resume_extracted=True,
                    resume_structured=True,
                    errors=[],
                ),
            )
        except Exception as e:
            logger.warning("Failed to validate cached structured resume for app %d: %s", application.id, e)

    # ── Step 2: Extract text from PDF ───────────────────────────────
    extraction = extract_text_from_pdf(application.resume.file)

    if not extraction.success:
        return build_candidate_data(
            application=application,
            structured_resume=None,
            processing=ProcessingStatus(
                success=False,
                has_resume=True,
                resume_extracted=False,
                resume_structured=False,
                errors=[extraction.error or "PDF text extraction failed"],
            ),
        )

    # ── Step 3: Structure resume via LLM ────────────────────────────
    structured_resume = None
    errors: list[str] = []

    try:
        structured_resume = structure_resume(extraction.text)
    except LLMProviderError:
        logger.exception(
            "LLM structuring failed for application %d",
            application.id,
        )
        errors.append("LLM resume structuring failed")
    except Exception:
        logger.exception(
            "Unexpected error during LLM structuring for application %d",
            application.id,
        )
        errors.append("Unexpected error during resume structuring")

    resume_structured = structured_resume is not None

    # ── Step 4: Check for degenerate LLM output ─────────────────────
    if structured_resume and _is_degenerate(structured_resume):
        errors.append("LLM returned minimal/empty structured data")

    success = resume_structured and not errors

    # ── Cache structured resume in CandidateScreeningRecord ─────────
    if structured_resume:
        try:
            CandidateScreeningRecord.objects.update_or_create(
                application=application,
                defaults={
                    "job": application.job,
                    "structured_resume": structured_resume.model_dump(exclude_none=True),
                    "resume_file_name": file_name,
                },
            )
        except Exception:
            logger.exception("Failed to cache screening record for app %d", application.id)

    return build_candidate_data(
        application=application,
        structured_resume=structured_resume,
        processing=ProcessingStatus(
            success=success,
            has_resume=True,
            resume_extracted=True,
            resume_structured=resume_structured,
            errors=errors,
        ),
    )


def _is_degenerate(resume) -> bool:
    """Check if a structured resume is essentially empty."""
    return (
        not resume.candidate_name
        and not resume.skills
        and not resume.experience
        and not resume.education
        and not resume.professional_summary
    )


def prepare_candidates_for_job(job: Job) -> JobScreeningResponse:
    """Run the full candidate data preparation pipeline for a job.

    Fetches all applications for the given job, processes each through
    the PDF extraction → LLM structuring → data building pipeline,
    and returns a complete JobScreeningResponse.

    Per-candidate errors never fail the entire request — each candidate
    gets its own ProcessingStatus with error details.

    Args:
        job: The Job model instance to process applications for.

    Returns:
        JobScreeningResponse with all candidate screening data.
    """
    applications = (
        Application.objects.select_related(
            "job",
            "seeker",
            "seeker__user",
            "resume",
        )
        .filter(job=job)
        .order_by("-created_at")
    )

    candidates: list[CandidateScreeningData] = []
    success_count = 0
    fail_count = 0

    for application in applications:
        logger.info(
            "Processing application %d (candidate: %s)",
            application.id,
            application.seeker.user.email,
        )

        candidate_data = _process_single_application(application)
        candidates.append(candidate_data)

        if candidate_data.processing.success:
            success_count += 1
        else:
            fail_count += 1

    logger.info(
        "Pipeline complete for job %d: %d/%d successful",
        job.id,
        success_count,
        len(candidates),
    )

    return JobScreeningResponse(
        job_id=job.id,
        job_title=job.title,
        total_applications=len(candidates),
        successfully_processed=success_count,
        failed_processing=fail_count,
        candidates=candidates,
    )
