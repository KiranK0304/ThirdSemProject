"""API views for resume screening and candidate ranking."""
from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from talentwright.jobs.models import Job
from talentwright.resume_screening.models import JobRankingSnapshot
from talentwright.resume_screening.schemas import (
    CopilotMessage,
    CopilotRequest,
    CopilotResponse,
    JobCriteriaResponse,
    JobRankingResponse,
)
from talentwright.resume_screening.services.copilot import execute_copilot_command
from talentwright.resume_screening.services.pipeline import prepare_candidates_for_job
from talentwright.resume_screening.services.ranker import rank_candidates
from talentwright.resume_screening.services.weights import get_job_weights
from talentwright.resume_screening.services.weights import save_job_weights
from talentwright.users.api.permissions import IsVerifiedEmployer

logger = logging.getLogger(__name__)


def _get_employer_job(request, job_id: int) -> Job:
    """Helper to verify employer owns the requested job."""
    return get_object_or_404(
        Job.objects.select_related("employer"),
        pk=job_id,
        employer=request.user.employer_profile,
    )


class JobScreeningPrepareView(APIView):
    """Prepare candidate screening data for a job.

    Processes all applications for the specified job by extracting
    resume text, structuring it via LLM, and combining it with
    application data.

    POST /api/screening/jobs/<job_id>/prepare/
    """

    permission_classes = [IsVerifiedEmployer]

    def post(self, request, job_id):
        job = _get_employer_job(request, job_id)

        logger.info(
            "Screening preparation requested for job %d by user %s",
            job.id,
            request.user.email,
        )

        result = prepare_candidates_for_job(job)

        return Response(
            result.model_dump(),
            status=status.HTTP_200_OK,
        )


class JobScreeningCriteriaView(APIView):
    """Manage scoring criteria and weights for a job.

    GET /api/screening/jobs/<job_id>/criteria/
        Returns current scoring criteria weights (or system defaults if not set).

    PUT / POST /api/screening/jobs/<job_id>/criteria/
        Updates or sets scoring criteria weights for the job.
        Payload:
            {
                "weights": {
                    "experience": 0.50,
                    "skills": 0.20,
                    "projects": 0.30
                }
            }
    """

    permission_classes = [IsVerifiedEmployer]

    def get(self, request, job_id):
        job = _get_employer_job(request, job_id)
        weights, is_custom = get_job_weights(job)

        response_data = JobCriteriaResponse(
            job_id=job.id,
            weights=weights,
            is_custom=is_custom,
        )
        return Response(response_data.model_dump(), status=status.HTTP_200_OK)

    def put(self, request, job_id):
        return self._save_weights(request, job_id)

    def post(self, request, job_id):
        return self._save_weights(request, job_id)

    def _save_weights(self, request, job_id):
        job = _get_employer_job(request, job_id)

        raw_weights = request.data.get("weights") if isinstance(request.data, dict) and "weights" in request.data else request.data
        if not isinstance(raw_weights, dict):
            raise ValidationError({"weights": "Must provide a dictionary of criteria to weights."})

        _, normalized_weights = save_job_weights(job, raw_weights)

        response_data = JobCriteriaResponse(
            job_id=job.id,
            weights=normalized_weights,
            is_custom=True,
        )
        return Response(response_data.model_dump(), status=status.HTTP_200_OK)


class JobScreeningRankView(APIView):
    """Evaluate and rank candidates for a job.

    POST /api/screening/jobs/<job_id>/rank/
        Triggers candidate evaluation and ranking.
        Optionally accepts custom weights in the request body:
            {
                "weights": {
                    "experience": 0.40,
                    "skills": 0.30,
                    "projects": 0.30
                }
            }
        If weights are not provided, uses the job's saved criteria (or defaults).
        Evaluates each candidate independently with the LLM, computes the
        deterministic backend weighted final score, sorts candidates descending,
        and saves a snapshot.

    GET /api/screening/jobs/<job_id>/rank/
        Retrieves the latest ranked candidate results for the job without
        re-running the LLM.
    """

    permission_classes = [IsVerifiedEmployer]

    def post(self, request, job_id):
        job = _get_employer_job(request, job_id)

        # ── 1. Determine weights to use ─────────────────────────────
        custom_weights = request.data.get("weights") if isinstance(request.data, dict) and "weights" in request.data else None
        if custom_weights:
            _, weights = save_job_weights(job, custom_weights)
        else:
            weights, _ = get_job_weights(job)

        logger.info(
            "Ranking requested for job %d by user %s with weights %s",
            job.id,
            request.user.email,
            weights,
        )

        # ── 2. Prepare candidate screening data ─────────────────────
        prepared_data = prepare_candidates_for_job(job)

        # ── 3. Rank candidates ──────────────────────────────────────
        ranking_response = rank_candidates(job, prepared_data.candidates, weights)

        return Response(
            ranking_response.model_dump(),
            status=status.HTTP_200_OK,
        )

    def get(self, request, job_id):
        job = _get_employer_job(request, job_id)

        latest_snapshot = (
            JobRankingSnapshot.objects.filter(job=job)
            .order_by("-created_at")
            .first()
        )

        if not latest_snapshot:
            return Response(
                {
                    "detail": "No ranking results found for this job. Trigger a ranking by sending a POST to this endpoint.",
                    "job_id": job.id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = JobRankingResponse(
            job_id=job.id,
            job_title=job.title,
            weights_used=latest_snapshot.weights_used,
            total_candidates=latest_snapshot.total_candidates,
            ranked_candidates=latest_snapshot.ranked_candidates,
            created_at=latest_snapshot.created_at.isoformat(),
        )

        return Response(response_data.model_dump(), status=status.HTTP_200_OK)


class JobScreeningCopilotView(APIView):
    """AI Recruiter Agent Copilot endpoint.

    POST /api/screening/jobs/<job_id>/copilot/
        Processes recruiter prompts, questions, candidate comparisons,
        and request for outreach/interview questions. Returns structured
        replies and one-click direct actions.
    """

    permission_classes = [IsVerifiedEmployer]

    def post(self, request, job_id):
        job = _get_employer_job(request, job_id)

        try:
            req_data = CopilotRequest.model_validate(request.data)
        except ValidationError as exc:
            return Response(exc.errors(), status=status.HTTP_400_BAD_REQUEST)

        response_data: CopilotResponse = execute_copilot_command(
            job=job,
            message=req_data.message,
            history=req_data.history,
            candidate_ids=req_data.candidate_ids,
        )

        return Response(response_data.model_dump(), status=status.HTTP_200_OK)
