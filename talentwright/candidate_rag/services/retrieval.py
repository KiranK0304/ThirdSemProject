"""Semantic retrieval service for querying candidate resume chunks and hydrating authoritative records."""

from __future__ import annotations

import logging
from typing import Any

from talentwright.candidate_rag.models import CandidateResumeChunk
from talentwright.candidate_rag.services.embeddings import EmbeddingClient
from talentwright.candidate_rag.services.vector_math import cosine_similarity

logger = logging.getLogger(__name__)


def search_candidate_chunks(
    job_id: int,
    query: str,
    limit: int = 5,
    min_similarity: float = 0.20,
    embedding_client: EmbeddingClient | None = None,
) -> list[dict[str, Any]]:
    """Retrieve semantically relevant candidates for a job and hydrate with PostgreSQL authoritative data.

    Args:
        job_id: The job posting ID to filter candidates against.
        query: The recruiter's search query (skill, experience, keyword).
        limit: Maximum number of distinct candidates to return (clamped 1-10).
        min_similarity: Minimum cosine similarity threshold to qualify as a match.
        embedding_client: Optional EmbeddingClient for dependency injection.

    Returns:
        A list of structured candidate dictionaries containing authoritative profile info
        and specific matched evidence excerpts.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    safe_limit = max(1, min(int(limit), 10))
    client = embedding_client or EmbeddingClient()

    try:
        query_vector = client.get_embedding(cleaned_query)
    except Exception as exc:
        logger.exception("Failed to embed search query '%s': %s", cleaned_query, exc)
        return []

    if not query_vector:
        return []

    # 1. Fetch chunks scoped to this specific job
    chunks_qs = (
        CandidateResumeChunk.objects.filter(job_id=job_id)
        .select_related("resume_analysis", "application__seeker__user")
    )
    chunks = list(chunks_qs)

    # Self-healing cold-start: if no chunks exist, check for completed records that need indexing
    if not chunks:
        from talentwright.candidate_rag.services.indexer import index_resume_analysis
        from talentwright.resume_analysis.models import AnalysisStatus
        from talentwright.resume_analysis.models import ResumeAnalysisRecord

        unindexed_records = list(
            ResumeAnalysisRecord.objects.filter(
                application__job_id=job_id,
                status=AnalysisStatus.COMPLETED,
            )
            .exclude(chunks__isnull=False)
            .distinct()
        )

        if unindexed_records:
            logger.info(
                "Self-healing: Found %d completed unindexed candidate records for Job #%d. Indexing on-demand.",
                len(unindexed_records),
                job_id,
            )
            for record in unindexed_records:
                try:
                    index_resume_analysis(record, embedding_client=client)
                except Exception as index_exc:  # noqa: BLE001
                    logger.warning(
                        "Self-healing indexing failed for Record #%d: %s",
                        record.id,
                        index_exc,
                    )

            # Re-fetch newly created chunks
            chunks = list(
                CandidateResumeChunk.objects.filter(job_id=job_id).select_related(
                    "resume_analysis", "application__seeker__user"
                )
            )

    if not chunks:
        logger.info("No indexed candidate chunks found for Job #%d", job_id)
        return []

    # 2. Compute cosine similarity for each chunk
    scored_chunks: list[tuple[float, CandidateResumeChunk]] = []
    for chunk in chunks:
        score = cosine_similarity(query_vector, chunk.embedding)
        if score >= min_similarity:
            scored_chunks.append((score, chunk))

    if not scored_chunks:
        logger.info("No candidate chunks exceeded similarity threshold %.2f for query '%s'", min_similarity, cleaned_query)
        return []

    # Sort chunks descending by similarity score
    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    # 3. Deduplicate by application_id and aggregate top evidence excerpts
    candidates_map: dict[int, dict[str, Any]] = {}

    for score, chunk in scored_chunks:
        app_id = chunk.application_id
        if app_id not in candidates_map:
            record = chunk.resume_analysis
            structured = record.structured_resume or {}
            scorecard = record.evaluation_scorecard or {}
            user = getattr(chunk.application.seeker, "user", None)
            name = (
                user.name
                if user and user.name
                else (user.email if user else f"Applicant #{app_id}")
            )
            email = user.email if user else ""

            candidates_map[app_id] = {
                "application_id": app_id,
                "name": name,
                "email": email,
                "overall_score": (
                    float(record.overall_score)
                    if record.overall_score is not None
                    else 0.0
                ),
                "recommendation": record.recommendation or "N/A",
                "years_experience": structured.get("total_years_experience", 0.0),
                "key_skills": (structured.get("skills") or [])[:10],
                "summary": (
                    structured.get("summary")
                    or scorecard.get("summary")
                    or "No summary provided."
                ),
                "relevant_evidence": [],
                "_top_similarity": score,
            }

        # Keep up to 3 best matching evidence chunks per candidate
        if len(candidates_map[app_id]["relevant_evidence"]) < 3:
            section_title = chunk.chunk_type.replace("_", " ").title()
            candidates_map[app_id]["relevant_evidence"].append(
                {
                    "section": section_title,
                    "details": chunk.content,
                }
            )

    # 4. Sort candidates by their top matching evidence similarity
    ranked_candidates = sorted(
        candidates_map.values(),
        key=lambda c: c["_top_similarity"],
        reverse=True,
    )[:safe_limit]

    # Clean internal sorting key
    for candidate in ranked_candidates:
        candidate.pop("_top_similarity", None)

    logger.info(
        "Semantic search returned %d candidates for Job #%d (query='%s')",
        len(ranked_candidates),
        job_id,
        cleaned_query,
    )
    return ranked_candidates
