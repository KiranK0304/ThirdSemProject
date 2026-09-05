"""API views for resume screening."""
from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talentwright.jobs.models import Job
from talentwright.resume_screening.services.pipeline import prepare_candidates_for_job
from talentwright.users.api.permissions import IsVerifiedEmployer

logger = logging.getLogger(__name__)


class JobScreeningPrepareView(APIView):
    """Prepare candidate screening data for a job.

    Processes all applications for the specified job by extracting
    resume text, structuring it via LLM, and combining it with
    application data.

    POST /api/screening/jobs/<job_id>/prepare/
    """

    permission_classes = [IsVerifiedEmployer]

    def post(self, request, job_id):
        job = get_object_or_404(
            Job.objects.select_related("employer"),
            pk=job_id,
            employer=request.user.employer_profile,
        )

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
