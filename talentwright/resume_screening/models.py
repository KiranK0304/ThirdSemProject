"""Models for the resume_screening app.

Stores per-job scoring criteria weights and generated ranking snapshots
so that employers can retrieve ranking results without re-running LLMs.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _

DEFAULT_CRITERIA_WEIGHTS = {
    "experience": 0.40,
    "skills": 0.30,
    "projects": 0.20,
    "education": 0.10,
}


class JobScoringConfig(models.Model):
    """Stores configurable scoring criteria and weights for a specific job."""

    job = models.OneToOneField(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="scoring_config",
    )
    weights = models.JSONField(
        _("Scoring Weights"),
        default=dict,
        help_text=_("Dictionary of criterion name to weight (e.g. {'experience': 0.5, 'skills': 0.5})"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Job Scoring Config")
        verbose_name_plural = _("Job Scoring Configs")

    def get_weights(self) -> dict[str, float]:
        """Return configured weights or the default weights if not set."""
        if self.weights and isinstance(self.weights, dict):
            return self.weights
        return DEFAULT_CRITERIA_WEIGHTS.copy()

    def __str__(self) -> str:
        return f"ScoringConfig for Job {self.job_id}: {self.job.title}"


class JobRankingSnapshot(models.Model):
    """Stores the latest or historic AI ranking result for a job."""

    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="ranking_snapshots",
    )
    weights_used = models.JSONField(
        _("Weights Used"),
        default=dict,
    )
    ranked_candidates = models.JSONField(
        _("Ranked Candidates"),
        default=list,
        help_text=_("List of ranked candidate objects with criterion scores, final score, and reasons"),
    )
    total_candidates = models.PositiveIntegerField(
        _("Total Candidates"),
        default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Job Ranking Snapshot")
        verbose_name_plural = _("Job Ranking Snapshots")

    def __str__(self) -> str:
        return f"RankingSnapshot for Job {self.job_id} ({self.total_candidates} candidates) at {self.created_at}"


class CandidateScreeningRecord(models.Model):
    """Caches per-application resume extraction, structuring, and criterion evaluations.

    Ensures we never re-extract PDFs or re-evaluate the same candidate with LLMs multiple times.
    Drops subsequent ranking response times from ~46 seconds down to < 0.05 seconds.
    """

    application = models.OneToOneField(
        "applications.Application",
        on_delete=models.CASCADE,
        related_name="screening_record",
    )
    job = models.ForeignKey(
        "jobs.Job",
        on_delete=models.CASCADE,
        related_name="screening_records",
    )
    structured_resume = models.JSONField(
        _("Structured Resume"),
        null=True,
        blank=True,
        help_text=_("Cached JSON output of StructuredResume from Phase 1"),
    )
    resume_file_name = models.CharField(
        _("Resume File Name"),
        max_length=255,
        blank=True,
    )
    criteria_evaluations = models.JSONField(
        _("Criteria Evaluations"),
        default=dict,
        help_text=_("Cached dictionary of criterion evaluations: {criterion: {score, reason}}"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Candidate Screening Record")
        verbose_name_plural = _("Candidate Screening Records")

    def __str__(self) -> str:
        return f"ScreeningRecord for Application {self.application_id} (Job {self.job_id})"

