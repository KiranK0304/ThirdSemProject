"""Database models for resume analysis and persistent evaluations."""

from __future__ import annotations

from django.db import models
from django.db.models import CASCADE
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import JSONField
from django.db.models import OneToOneField
from django.db.models import TextChoices
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _


class AnalysisStatus(TextChoices):
    """Lifecycle status of a resume analysis process."""

    PENDING = "PENDING", _("Pending")
    PROCESSING = "PROCESSING", _("Processing")
    COMPLETED = "COMPLETED", _("Completed")
    FAILED = "FAILED", _("Failed")


class ResumeAnalysisRecord(models.Model):
    """Stores the parsed structured resume and baseline evaluation scorecard."""

    application = OneToOneField(
        "applications.Application",
        on_delete=CASCADE,
        related_name="resume_analysis",
    )
    status = CharField(
        _("Status"),
        max_length=20,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.PENDING,
        db_index=True,
    )
    overall_score = DecimalField(
        _("Overall Score"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        db_index=True,
    )
    recommendation = CharField(
        _("Recommendation"),
        max_length=30,
        blank=True,
    )
    structured_resume = JSONField(
        _("Structured Resume"),
        default=dict,
        blank=True,
    )
    evaluation_scorecard = JSONField(
        _("Evaluation Scorecard"),
        default=dict,
        blank=True,
    )
    raw_text = TextField(
        _("Raw Resume Text"),
        blank=True,
    )
    error_message = TextField(
        _("Error Message"),
        blank=True,
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Resume Analysis Record")
        verbose_name_plural = _("Resume Analysis Records")

    def __str__(self) -> str:
        score_display = (
            f"{self.overall_score}" if self.overall_score is not None else "N/A"
        )
        return f"Analysis for Application #{self.application_id} ({self.status}) - Score: {score_display}"
