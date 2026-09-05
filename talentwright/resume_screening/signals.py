"""Django signals for resume screening.

Listens for new Application creation events and automatically processes,
structures, and evaluates the new candidate in a background thread.
Updates the job's ranking snapshot so that employers immediately see the
new candidate scored and placed in the leaderboard without waiting.
"""
from __future__ import annotations

import logging
import threading

from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver

from talentwright.applications.models import Application

logger = logging.getLogger(__name__)


def _process_new_application_worker(application_id: int) -> None:
    """Background worker function to extract, structure, and rank a new applicant."""
    # Close any stale connection inherited from parent thread
    connection.close()

    try:
        from talentwright.resume_screening.services.pipeline import (
            _process_single_application,
            prepare_candidates_for_job,
        )
        from talentwright.resume_screening.services.ranker import (
            evaluate_single_candidate,
            rank_candidates,
        )
        from talentwright.resume_screening.services.weights import get_job_weights

        application = (
            Application.objects.select_related(
                "job",
                "seeker",
                "seeker__user",
                "resume",
            )
            .filter(pk=application_id)
            .first()
        )

        if not application:
            logger.warning("Background worker: Application %d not found", application_id)
            return

        logger.info(
            "Auto-screening triggered for new application %d (job %d, seeker %s)",
            application.id,
            application.job_id,
            application.seeker.user.email,
        )

        # 1. Extract PDF and structure resume with LLM (cached in CandidateScreeningRecord)
        candidate_data = _process_single_application(application)

        # 2. Get current criteria weights for this job
        weights, _ = get_job_weights(application.job)
        criteria = list(weights.keys())

        # 3. Evaluate candidate criteria with LLM (cached in CandidateScreeningRecord)
        evaluate_single_candidate(application.job, candidate_data, criteria)

        # 4. Re-rank all applicants for this job and update the ranking snapshot
        all_candidates_prep = prepare_candidates_for_job(application.job)
        rank_candidates(application.job, all_candidates_prep.candidates, weights)

        logger.info(
            "Auto-screening & re-ranking successfully completed for application %d",
            application.id,
        )

    except Exception:
        logger.exception(
            "Error in background auto-screening for application %d",
            application_id,
        )
    finally:
        connection.close()


@receiver(post_save, sender=Application)
def on_new_application_submitted(sender, instance: Application, created: bool, **kwargs):
    """Signal receiver triggered when an Application is saved.

    If a new application is created (created=True), kicks off a background thread
    to automatically extract, structure, evaluate, and append to the ranking snapshot.
    """
    if not created:
        return

    import os
    if "PYTEST_CURRENT_TEST" in os.environ:
        # Skip spawning background threads in isolated pytest test runner
        return

    # Run in a background daemon thread so applicant HTTP request responds in < 100ms
    thread = threading.Thread(
        target=_process_new_application_worker,
        args=(instance.id,),
        name=f"auto-screen-app-{instance.id}",
        daemon=True,
    )
    thread.start()
    logger.info(
        "Started background auto-screening thread for application %d",
        instance.id,
    )
