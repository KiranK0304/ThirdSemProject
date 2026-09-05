"""Database models for the Recruiter AI Copilot chat sessions and messages."""

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


class MessageRole(TextChoices):
    """Origin of a copilot chat message."""

    USER = "USER", _("User")
    ASSISTANT = "ASSISTANT", _("Assistant")
    SYSTEM = "SYSTEM", _("System")


class CopilotSession(models.Model):
    """A chat conversation thread scoped to a specific job and employer."""

    job = ForeignKey(
        "jobs.Job",
        on_delete=CASCADE,
        related_name="copilot_sessions",
    )
    employer = ForeignKey(
        "users.EmployerProfile",
        on_delete=CASCADE,
        related_name="copilot_sessions",
    )
    title = CharField(
        _("Session Title"),
        max_length=255,
        blank=True,
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = _("Copilot Session")
        verbose_name_plural = _("Copilot Sessions")

    def __str__(self) -> str:
        return f"Session #{self.id} - {self.title or f'Job #{self.job_id}'}"


class CopilotMessage(models.Model):
    """An individual message within a recruiter chat session."""

    session = ForeignKey(
        CopilotSession,
        on_delete=CASCADE,
        related_name="messages",
    )
    role = CharField(
        _("Role"),
        max_length=15,
        choices=MessageRole.choices,
        default=MessageRole.USER,
    )
    content = TextField(_("Content"))
    metadata = JSONField(
        _("Metadata"),
        default=dict,
        blank=True,
    )
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Copilot Message")
        verbose_name_plural = _("Copilot Messages")

    def __str__(self) -> str:
        snippet = self.content[:40] if self.content else "(empty)"
        return f"[{self.role}] #{self.id}: {snippet}"
