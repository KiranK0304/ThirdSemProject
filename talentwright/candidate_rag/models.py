"""Database models for candidate resume chunking and vector representations."""

from __future__ import annotations

from django.db import models
from django.db.models import CASCADE
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import JSONField
from django.db.models import TextChoices
from django.db.models import TextField
from django.utils.translation import gettext_lazy as _


class ChunkType(TextChoices):
    """Types of semantic chunks extracted from a structured resume."""

    WORK_EXPERIENCE = "WORK_EXPERIENCE", _("Work Experience")
    SKILLS_SUMMARY = "SKILLS_SUMMARY", _("Skills and Summary")
    PROJECT = "PROJECT", _("Project")
    EDUCATION_CERTIFICATIONS = "EDUCATION_CERTIFICATIONS", _("Education and Certifications")


class CandidateResumeChunk(models.Model):
    """A semantic text chunk with embedding vector linked to an application and resume analysis."""

    application = ForeignKey(
        "applications.Application",
        on_delete=CASCADE,
        related_name="resume_chunks",
    )
    job = ForeignKey(
        "jobs.Job",
        on_delete=CASCADE,
        related_name="candidate_resume_chunks",
        db_index=True,
    )
    resume_analysis = ForeignKey(
        "resume_analysis.ResumeAnalysisRecord",
        on_delete=CASCADE,
        related_name="chunks",
    )
    candidate_name = CharField(
        _("Candidate Name"),
        max_length=255,
        blank=True,
    )
    chunk_type = CharField(
        _("Chunk Type"),
        max_length=32,
        choices=ChunkType.choices,
        db_index=True,
    )
    content = TextField(
        _("Chunk Content"),
    )
    metadata = JSONField(
        _("Chunk Metadata"),
        default=dict,
        blank=True,
    )
    embedding = JSONField(
        _("Embedding Vector"),
        default=list,
        blank=True,
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["application", "id"]
        verbose_name = _("Candidate Resume Chunk")
        verbose_name_plural = _("Candidate Resume Chunks")
        indexes = [
            models.Index(fields=["job", "chunk_type"], name="rag_job_chunk_type_idx"),
            models.Index(fields=["application", "chunk_type"], name="rag_app_chunk_type_idx"),
        ]

    def __str__(self) -> str:
        name_display = self.candidate_name or f"App #{self.application_id}"
        return f"{name_display} - [{self.chunk_type}] (Job #{self.job_id})"
