"""End-to-end resume analysis pipeline orchestrating extraction, parsing, and evaluation."""

from __future__ import annotations

from decimal import Decimal
import logging

from talentwright.applications.models import Application
from talentwright.resume_analysis.evaluation_schemas import JobContext
from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord
from talentwright.resume_analysis.services.evaluator import evaluate_resume
from talentwright.resume_analysis.services.llm_client import LLMClient
from talentwright.resume_analysis.services.parser import parse_resume_text
from talentwright.resume_analysis.services.text_extractor import extract_text_from_file

logger = logging.getLogger(__name__)


def analyze_application(
    application: Application | int,
    llm_client: LLMClient | None = None,
) -> ResumeAnalysisRecord:
    """Run full automated analysis on a job application.

    Extracts text from the attached resume, structures the candidate data via LLM,
    and evaluates candidate fit against the job criteria.

    Args:
        application: An Application model instance or integer primary key.
        llm_client: Optional LLMClient instance for dependency injection.

    Returns:
        ResumeAnalysisRecord: The updated or created analysis record.
    """
    if isinstance(application, (int, str)):
        application = Application.objects.select_related("job", "seeker", "resume").get(
            id=int(application)
        )

    record, _ = ResumeAnalysisRecord.objects.get_or_create(application=application)

    # 1. Resolve resume file
    resume = application.resume
    if not resume and application.seeker:
        resume = (
            application.seeker.resumes.filter(is_primary=True).first()
            or application.seeker.resumes.first()
        )

    if not resume or not resume.file:
        record.status = AnalysisStatus.FAILED
        record.error_message = (
            "No resume document found for this application or seeker."
        )
        record.save()
        logger.warning("Application #%d has no resume file attached.", application.id)
        return record

    record.status = AnalysisStatus.PROCESSING
    record.error_message = ""
    record.save(update_fields=["status", "error_message", "updated_at"])

    try:
        # Step A: Text Extraction
        raw_text = extract_text_from_file(
            file_source=resume.file,
            filename=resume.file.name,
        )
        record.raw_text = raw_text

        # Step B: LLM Information Parsing
        structured_resume = parse_resume_text(
            resume_text=raw_text,
            llm_client=llm_client,
        )
        record.structured_resume = structured_resume.model_dump()

        # Step C: Job Context Construction (TypedDict)
        job = application.job
        job_context: JobContext = {
            "job_id": job.id,
            "title": job.title,
            "description": job.description,
            "cover_letter": application.cover_letter or "",
        }

        # Step D: Objective Baseline Evaluation
        scorecard = evaluate_resume(
            resume=structured_resume,
            job_context=job_context,
            llm_client=llm_client,
        )
        record.evaluation_scorecard = scorecard.model_dump()
        record.overall_score = Decimal(str(round(scorecard.overall_score, 2)))
        record.recommendation = scorecard.recommendation
        record.status = AnalysisStatus.COMPLETED
        record.save()

        logger.info(
            "Analysis completed for Application #%d (Score: %s, Recommendation: %s)",
            application.id,
            record.overall_score,
            record.recommendation,
        )

        # Step E: Automatic Candidate RAG Indexing (Non-blocking: analysis stays COMPLETED if RAG fails)
        try:
            from talentwright.candidate_rag.services.indexer import index_resume_analysis

            index_resume_analysis(record)
        except Exception as rag_exc:  # noqa: BLE001
            logger.error(
                "RAG indexing failed for Application #%d (Record #%d): %s. "
                "The analysis record remains successfully saved and can be retried via "
                "'manage.py index_candidate_resumes --unindexed-only'.",
                application.id,
                record.id,
                rag_exc,
                exc_info=True,
            )

    except Exception as exc:
        logger.exception("Analysis failed for Application #%d: %s", application.id, exc)
        record.status = AnalysisStatus.FAILED
        record.error_message = str(exc)
        record.save()

    return record
