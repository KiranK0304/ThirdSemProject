"""Search tool querying candidates semantically using candidate_rag."""

from __future__ import annotations

import logging
from typing import Any

from talentwright.candidate_rag.services.retrieval import search_candidate_chunks

logger = logging.getLogger(__name__)


def search_candidates(
    job_id: int,
    query: str = "",
    limit: Any = 5,
) -> list[dict[str, Any]]:
    """Search candidates for a job based on semantic query criteria.

    Args:
        job_id: Primary key of the job posting (injected securely from session context).
        query: Specific technical skill, technology, or domain experience.
        limit: Maximum number of candidates to return (default is 5, max 10).

    Returns:
        List of matching candidate profiles with evidence excerpts.
    """
    try:
        raw_limit = int(limit) if limit is not None else 5
    except (ValueError, TypeError):
        raw_limit = 5
    safe_limit = max(1, min(raw_limit, 10))

    cleaned_query = (query or "").strip()
    if not cleaned_query:
        logger.warning(
            "search_candidates invoked for Job #%d with empty query; returning empty list",
            job_id,
        )
        return []

    logger.info(
        "search_candidates tool invoked for Job #%d with query '%s' (limit=%d)",
        job_id,
        cleaned_query,
        safe_limit,
    )
    return search_candidate_chunks(job_id=job_id, query=cleaned_query, limit=safe_limit)
