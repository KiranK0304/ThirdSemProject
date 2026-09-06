"""Signals for automatic background resume analysis on new applications."""

from __future__ import annotations

import logging
import os
import threading

from django.db import connection
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from talentwright.applications.models import Application
from talentwright.resume_analysis.services.pipeline import analyze_application

logger = logging.getLogger(__name__)


def _background_analysis_worker(application_id: int) -> None:
    """Worker function executed in a background daemon thread."""
    try:
        analyze_application(application_id)
    except Exception:
        logger.exception(
            "Unhandled error in background analysis worker for application #%d",
            application_id,
        )
    finally:
        connection.close()


def spawn_analysis_thread(application_id: int) -> None:
    """Spawn a background daemon thread to run resume analysis."""
    thread = threading.Thread(
        target=_background_analysis_worker,
        args=(application_id,),
        name=f"resume-analysis-app-{application_id}",
        daemon=True,
    )
    thread.start()
    logger.info(
        "Spawned background analysis thread for application #%d",
        application_id,
    )


@receiver(post_save, sender=Application)
def on_application_created(
    sender: type[Application],
    instance: Application,
    created: bool,
    **kwargs,
) -> None:
    """Trigger background analysis when a new application is submitted."""
    if not created:
        return

    if "PYTEST_CURRENT_TEST" in os.environ:
        # Avoid uncoordinated background threads during automated test runs
        return

    transaction.on_commit(lambda: spawn_analysis_thread(instance.id))
