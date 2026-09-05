"""Candidate evaluation and ranking service.

Evaluates each candidate independently using the LLM against the job
requirements and user-configured scoring criteria.
Calculates the final weighted score deterministically in Python (backend):
    Final Score = Σ (Criterion Score × Criterion Weight)
Sorts and ranks candidates from highest to lowest score.
"""
from __future__ import annotations

import json
import logging

from talentwright.jobs.models import Job
from talentwright.resume_screening.models import JobRankingSnapshot
from talentwright.resume_screening.prompts import build_candidate_evaluation_prompt
from talentwright.resume_screening.schemas import (
    CandidateEvaluationResponse,
    CandidateScreeningData,
    CriterionDetail,
    JobRankingResponse,
    RankedCandidate,
)
from talentwright.resume_screening.services.llm_provider import (
    LLMProviderError,
    get_llm_provider,
)

logger = logging.getLogger(__name__)


def evaluate_single_candidate(
    job: Job,
    candidate: CandidateScreeningData,
    criteria: list[str],
) -> tuple[dict[str, int], dict[str, CriterionDetail]]:
    """Evaluate a single candidate independently across all criteria using the LLM.

    Each candidate is evaluated in isolation against the job description.
    No other candidate's information is passed to the LLM.

    Args:
        job: The Job model instance.
        candidate: The CandidateScreeningData for this applicant.
        criteria: List of criteria names to score (e.g. ['experience', 'skills']).

    Returns:
        Tuple of (criteria_scores: dict[str, int], criteria_details: dict[str, CriterionDetail]).
    """
    # ── Fallback if no resume or extraction failed ──────────────────
    if not candidate.processing.has_resume or not candidate.resume:
        reason_msg = "No resume attached to this application."
        if candidate.processing.errors:
            reason_msg = "; ".join(candidate.processing.errors)

        scores = {c: 0 for c in criteria}
        details = {c: CriterionDetail(score=0, reason=reason_msg) for c in criteria}
        return scores, details

    # ── Check if criteria evaluations are already cached in DB ──────
    from talentwright.resume_screening.models import CandidateScreeningRecord

    app_id = candidate.application.application_id
    record = CandidateScreeningRecord.objects.filter(application_id=app_id).first()

    if record and record.criteria_evaluations:
        cached_evals = record.criteria_evaluations
        if all(c.strip().lower() in cached_evals for c in criteria):
            scores = {}
            details = {}
            for c in criteria:
                data = cached_evals[c.strip().lower()]
                scores[c] = data["score"]
                details[c] = CriterionDetail(score=data["score"], reason=data["reason"])
            return scores, details

    # ── Prepare resume JSON for prompt ──────────────────────────────
    resume_dict = candidate.resume.model_dump(exclude_none=True)
    resume_json = json.dumps(resume_dict, indent=2)

    schema_json = json.dumps(
        CandidateEvaluationResponse.model_json_schema(),
        indent=2,
    )

    prompt = build_candidate_evaluation_prompt(
        job_title=job.title,
        job_description=job.description,
        candidate_name=candidate.application.candidate_name,
        candidate_email=candidate.application.candidate_email,
        cover_letter=candidate.application.cover_letter,
        resume_json=resume_json,
        criteria=criteria,
        schema_json=schema_json,
    )

    provider = get_llm_provider()

    try:
        response: CandidateEvaluationResponse = provider.generate_structured(
            prompt=prompt,
            response_schema=CandidateEvaluationResponse,
            temperature=0.0,
        )
    except LLMProviderError as exc:
        logger.exception(
            "LLM evaluation failed for application %d",
            candidate.application.application_id,
        )
        scores = {c: 0 for c in criteria}
        details = {
            c: CriterionDetail(score=0, reason=f"Evaluation error: {exc}")
            for c in criteria
        }
        return scores, details
    except Exception as exc:
        logger.exception(
            "Unexpected error evaluating application %d",
            candidate.application.application_id,
        )
        scores = {c: 0 for c in criteria}
        details = {
            c: CriterionDetail(score=0, reason="Unexpected evaluation failure")
            for c in criteria
        }
        return scores, details

    # ── Map LLM response items to the requested criteria ────────────
    eval_map = {}
    for item in response.evaluations:
        eval_map[item.criterion.strip().lower()] = item

    scores: dict[str, int] = {}
    details: dict[str, CriterionDetail] = {}

    for criterion in criteria:
        norm_key = criterion.strip().lower()
        if norm_key in eval_map:
            item = eval_map[norm_key]
            clamped_score = max(0, min(100, item.score))
            scores[criterion] = clamped_score
            details[criterion] = CriterionDetail(
                score=clamped_score,
                reason=item.reason or "No explanation provided.",
            )
        else:
            # Check for partial match
            matched = False
            for k, v in eval_map.items():
                if norm_key in k or k in norm_key:
                    clamped_score = max(0, min(100, v.score))
                    scores[criterion] = clamped_score
                    details[criterion] = CriterionDetail(
                        score=clamped_score,
                        reason=v.reason or "No explanation provided.",
                    )
                    matched = True
                    break
            if not matched:
                scores[criterion] = 0
                details[criterion] = CriterionDetail(
                    score=0,
                    reason="Criterion was not evaluated by the model.",
                )

    # ── Persist criteria evaluations to DB cache ────────────────────
    try:
        from talentwright.applications.models import Application
        if record:
            updated_evals = dict(record.criteria_evaluations or {})
            for c, detail in details.items():
                updated_evals[c.strip().lower()] = {"score": detail.score, "reason": detail.reason}
            record.criteria_evaluations = updated_evals
            record.save(update_fields=["criteria_evaluations", "updated_at"])
        elif Application.objects.filter(id=app_id).exists():
            CandidateScreeningRecord.objects.create(
                application_id=app_id,
                job=job,
                criteria_evaluations={
                    c.strip().lower(): {"score": detail.score, "reason": detail.reason}
                    for c, detail in details.items()
                },
            )
    except Exception:
        logger.exception("Failed to save criteria evaluations for application %d", app_id)

    return scores, details


def calculate_final_score(
    criteria_scores: dict[str, int],
    weights: dict[str, float],
) -> float:
    """Calculate the final weighted score deterministically.

    Formula:
        Final Score = Σ (Criterion Score × Criterion Weight)

    Because weights sum to 1.0, the final score is naturally 0 to 100.

    Args:
        criteria_scores: Dict of criterion name to score (0-100).
        weights: Dict of criterion name to weight (summing to 1.0).

    Returns:
        Final score rounded to 1 decimal place.
    """
    total = sum(criteria_scores.get(c, 0) * w for c, w in weights.items())
    return round(total, 1)


def rank_candidates(
    job: Job,
    candidates: list[CandidateScreeningData],
    weights: dict[str, float],
) -> JobRankingResponse:
    """Evaluate, score, and rank all candidates for a job.

    1. Evaluates each candidate independently.
    2. Calculates backend weighted final score.
    3. Sorts descending by final score.
    4. Assigns rank positions (1 to N).
    5. Saves a snapshot to the database.

    Args:
        job: The Job model instance.
        candidates: List of CandidateScreeningData objects.
        weights: Normalized scoring weights.

    Returns:
        JobRankingResponse containing all ranked candidates.
    """
    criteria = list(weights.keys())
    evaluated_list: list[dict] = []

    logger.info(
        "Starting candidate ranking for job %d (%s) with %d candidates. Criteria: %s",
        job.id,
        job.title,
        len(candidates),
        criteria,
    )

    for candidate in candidates:
        scores, details = evaluate_single_candidate(job, candidate, criteria)
        final_score = calculate_final_score(scores, weights)

        evaluated_list.append({
            "candidate_id": candidate.application.candidate_id,
            "application_id": candidate.application.application_id,
            "candidate_name": candidate.application.candidate_name,
            "candidate_email": candidate.application.candidate_email,
            "criteria_scores": scores,
            "criteria_details": details,
            "final_score": final_score,
        })

    # ── Sort descending by final_score (tie-breaker: application_id asc) ──
    evaluated_list.sort(
        key=lambda x: (-x["final_score"], x["application_id"])
    )

    # ── Assign rank positions ───────────────────────────────────────
    ranked_candidates: list[RankedCandidate] = []
    for idx, item in enumerate(evaluated_list, start=1):
        ranked_candidates.append(
            RankedCandidate(
                rank=idx,
                candidate_id=item["candidate_id"],
                application_id=item["application_id"],
                candidate_name=item["candidate_name"],
                candidate_email=item["candidate_email"],
                criteria_scores=item["criteria_scores"],
                criteria_details=item["criteria_details"],
                final_score=item["final_score"],
            )
        )

    # ── Save snapshot to database ───────────────────────────────────
    snapshot_candidates_json = [c.model_dump() for c in ranked_candidates]
    snapshot = JobRankingSnapshot.objects.create(
        job=job,
        weights_used=weights,
        ranked_candidates=snapshot_candidates_json,
        total_candidates=len(ranked_candidates),
    )

    logger.info(
        "Ranking complete for job %d. Snapshot ID: %d, Top candidate: %s (score: %.1f)",
        job.id,
        snapshot.id,
        ranked_candidates[0].candidate_name if ranked_candidates else "None",
        ranked_candidates[0].final_score if ranked_candidates else 0.0,
    )

    return JobRankingResponse(
        job_id=job.id,
        job_title=job.title,
        weights_used=weights,
        total_candidates=len(ranked_candidates),
        ranked_candidates=ranked_candidates,
        created_at=snapshot.created_at.isoformat(),
    )
