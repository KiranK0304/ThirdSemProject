"""Indexing service for creating vector chunks from ResumeAnalysisRecord."""

from __future__ import annotations

import logging
from typing import Sequence

from django.db import transaction

from talentwright.candidate_rag.models import CandidateResumeChunk
from talentwright.candidate_rag.services.chunker import generate_resume_chunks
from talentwright.candidate_rag.services.embeddings import EmbeddingClient
from talentwright.resume_analysis.models import ResumeAnalysisRecord

logger = logging.getLogger(__name__)


def index_resume_analysis(
    record: ResumeAnalysisRecord,
    embedding_client: EmbeddingClient | None = None,
) -> list[CandidateResumeChunk]:
    """Extract semantic chunks from a resume analysis record, compute embeddings, and store them.

    This operation is strictly idempotent. If chunks already exist for this application,
    they are atomically replaced with new ones.

    Args:
        record: The ResumeAnalysisRecord to index.
        embedding_client: Optional EmbeddingClient instance for dependency injection.

    Returns:
        A list of created CandidateResumeChunk instances.
    """
    structured_resume = record.structured_resume
    if not structured_resume or not isinstance(structured_resume, dict):
        logger.info(
            "ResumeAnalysisRecord #%d has no structured resume data to index.",
            record.id,
        )
        return []

    application = record.application
    job = application.job
    seeker = getattr(application, "seeker", None)
    user = getattr(seeker, "user", None) if seeker else None
    candidate_name = (
        user.name if user and user.name else (user.email if user else f"Applicant #{application.id}")
    )

    # 1. Generate semantic chunks
    chunks_data = generate_resume_chunks(
        structured_resume=structured_resume,
        candidate_name=candidate_name,
    )
    if not chunks_data:
        logger.warning(
            "No semantic chunks generated for Application #%d (Record #%d).",
            application.id,
            record.id,
        )
        return []

    # 2. Compute embeddings in batch
    client = embedding_client or EmbeddingClient()
    chunk_texts = [c["content"] for c in chunks_data]
    embeddings = client.get_embeddings_batch(chunk_texts)

    if len(embeddings) != len(chunks_data):
        msg = (
            f"Embedding count mismatch for Application #{application.id}: "
            f"expected {len(chunks_data)}, got {len(embeddings)}"
        )
        logger.error(msg)
        raise ValueError(msg)

    # 3. Save chunks atomically (idempotent replacement)
    with transaction.atomic():
        CandidateResumeChunk.objects.filter(application=application).delete()

        chunks_to_create = [
            CandidateResumeChunk(
                application=application,
                job=job,
                resume_analysis=record,
                candidate_name=candidate_name,
                chunk_type=c["chunk_type"],
                content=c["content"],
                metadata=c.get("metadata", {}),
                embedding=emb,
            )
            for c, emb in zip(chunks_data, embeddings)
        ]
        created_chunks = CandidateResumeChunk.objects.bulk_create(chunks_to_create)

    logger.info(
        "Successfully indexed %d chunks for Application #%d (Candidate: %s, Job #%d)",
        len(created_chunks),
        application.id,
        candidate_name,
        job.id,
    )
    return created_chunks
