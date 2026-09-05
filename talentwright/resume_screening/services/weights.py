"""Weights management and validation service.

Handles validation, normalization, and persistence of scoring weights.
Weights can be specified as decimals summing to 1.0 (e.g. 0.5, 0.3, 0.2)
or as percentages summing to 100 (e.g. 50, 30, 20).
"""
from __future__ import annotations

import logging
from typing import Any

from rest_framework.exceptions import ValidationError

from talentwright.jobs.models import Job
from talentwright.resume_screening.models import DEFAULT_CRITERIA_WEIGHTS
from talentwright.resume_screening.models import JobScoringConfig

logger = logging.getLogger(__name__)


def validate_and_normalize_weights(raw_weights: Any) -> dict[str, float]:
    """Validate and normalize user-provided scoring weights.

    Rules:
    - Must be a non-empty dictionary.
    - Keys must be non-empty strings.
    - Values must be numbers >= 0.
    - Sum of values must equal 1.0 (or 100%).
    - Automatically normalizes percentages (sum ~ 100) to decimals (sum = 1.0).

    Args:
        raw_weights: The dictionary of weights provided by user/frontend.

    Returns:
        Dictionary of normalized weights summing exactly to 1.0.

    Raises:
        ValidationError: If weights violate any validation rules.
    """
    if not isinstance(raw_weights, dict) or not raw_weights:
        raise ValidationError({"weights": "Weights must be a non-empty dictionary of criteria to numbers."})

    cleaned: dict[str, float] = {}
    for key, val in raw_weights.items():
        if not isinstance(key, str) or not key.strip():
            raise ValidationError({"weights": "All criteria names must be non-empty strings."})

        criterion = key.strip().lower()

        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise ValidationError({
                "weights": f"Weight for criterion '{criterion}' must be a number, got {type(val).__name__}."
            })

        if val < 0:
            raise ValidationError({
                "weights": f"Weight for criterion '{criterion}' must be non-negative, got {val}."
            })

        cleaned[criterion] = float(val)

    total = sum(cleaned.values())

    # Check if weights were provided as percentages summing to ~100
    if 99.0 <= total <= 101.0:
        cleaned = {k: v / total for k, v in cleaned.items()}
        total = sum(cleaned.values())

    # Allow slight floating point tolerance around 1.0
    if abs(total - 1.0) > 0.01:
        raise ValidationError({
            "weights": f"Weights must sum exactly to 1.0 (or 100%). Current sum is {round(total, 4)}."
        })

    # Exact normalization to avoid floating precision drift
    normalized = {k: round(v / total, 4) for k, v in cleaned.items()}
    # Adjust last item so sum is precisely 1.0
    drift = 1.0 - sum(normalized.values())
    if drift != 0:
        last_key = list(normalized.keys())[-1]
        normalized[last_key] = round(normalized[last_key] + drift, 4)

    return normalized


def get_job_weights(job: Job) -> tuple[dict[str, float], bool]:
    """Retrieve scoring weights for a job.

    Returns:
        Tuple of (weights_dict, is_custom_boolean).
        If the job has a saved JobScoringConfig, returns those weights and True.
        Otherwise, returns DEFAULT_CRITERIA_WEIGHTS and False.
    """
    try:
        config = JobScoringConfig.objects.filter(job=job).first()
        if config and config.weights:
            return config.weights, True
    except Exception:
        logger.exception("Error fetching scoring config for job %d", job.id)

    return DEFAULT_CRITERIA_WEIGHTS.copy(), False


def save_job_weights(job: Job, raw_weights: dict) -> tuple[JobScoringConfig, dict[str, float]]:
    """Validate, normalize, and save scoring weights for a job.

    Args:
        job: The Job model instance.
        raw_weights: The dictionary of weights to validate and save.

    Returns:
        Tuple of (JobScoringConfig instance, normalized_weights dict).
    """
    normalized = validate_and_normalize_weights(raw_weights)

    config, _ = JobScoringConfig.objects.update_or_create(
        job=job,
        defaults={"weights": normalized},
    )

    logger.info("Saved scoring weights for job %d: %s", job.id, normalized)
    return config, normalized
