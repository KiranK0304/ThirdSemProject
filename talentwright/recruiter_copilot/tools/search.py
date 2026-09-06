"""Search tool querying candidates semantically using candidate_rag."""

from __future__ import annotations

import logging
from typing import Any

from talentwright.candidate_rag.services.retrieval import search_candidate_chunks

logger = logging.getLogger(__name__)


def search_candidates(
    query: str,
    job_id: int,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Search candidates for a job based on semantic query criteria.

    Args:
        query: Specific technical skill, technology, or domain experience.
        job_id: Primary key of the job posting (injected securely from session context).
        limit: Maximum number of candidates to return (default is 5, max 10).

    Returns:
        List of matching candidate profiles with evidence excerpts.
    """
    safe_limit = max(1, min(int(limit), 10))
    logger.info(
        "search_candidates tool invoked for Job #%d with query '%s' (limit=%d)",
        job_id,
        query,
        safe_limit,
    )
    return search_candidate_chunks(job_id=job_id, query=query, limit=safe_limit)
