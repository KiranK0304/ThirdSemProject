from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CASCADE
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import TextChoices
from django.db.models import TextField
from django.db.models import UniqueConstraint
from django.db.models import URLField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from talentwright.jobs.models import JobStatus
from talentwright.users.models import VerificationStatus


class ApplicationStatus(TextChoices):
    SUBMITTED = "SUBMITTED", _("Submitted")
    UNDER_REVIEW = "UNDER_REVIEW", _("Under review")
    SHORTLISTED = "SHORTLISTED", _("Shortlisted")
    REJECTED = "REJECTED", _("Rejected")
    WITHDRAWN = "WITHDRAWN", _("Withdrawn")


class Application(models.Model):
    job = ForeignKey(
        "jobs.Job",
        on_delete=CASCADE,
        related_name="applications",
    )
    seeker = ForeignKey(
        "users.SeekerProfile",
        on_delete=CASCADE,
        related_name="applications",
    )
    resume = ForeignKey(
        "users.Resume",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    cover_letter = TextField(_("Cover letter"), blank=True)
    status = CharField(
        _("Status"),
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            UniqueConstraint(fields=["job", "seeker"], name="applications_application_job_seeker_unique"),
        ]

    def clean(self):
        super().clean()

        errors: dict[str, str] = {}
        if self.job_id:
            if self.job.status != JobStatus.OPEN:
                errors["job"] = _("Applications can only be submitted to open jobs.")
            elif self.job.employer.verification_status != VerificationStatus.APPROVED:
                errors["job"] = _("Applications can only be submitted to jobs from approved employers.")
        if self.resume_id and self.seeker_id:
            if self.resume.seeker_id != self.seeker_id:
                errors["resume"] = _("The attached resume must belong to the applicant.")
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"Application for {self.job_id} by {self.seeker_id}"

class InterviewStatus(TextChoices):
    SCHEDULED = "SCHEDULED", _("Scheduled")
    CANCELLED = "CANCELLED", _("Cancelled")
    COMPLETED = "COMPLETED", _("Completed")


class Interview(models.Model):
    application = models.OneToOneField(
        Application,
        on_delete=CASCADE,
        related_name="interview",
    )
    scheduled_at = DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    meeting_url = URLField(blank=True)
    notes = TextField(blank=True)
    status = CharField(
        max_length=20,
        choices=InterviewStatus.choices,
        default=InterviewStatus.SCHEDULED,
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_at"]

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        if self.scheduled_at and self.status == InterviewStatus.SCHEDULED and self.scheduled_at <= timezone.now():
            errors["scheduled_at"] = _("An interview must be scheduled for a future time.")
        if not 15 <= self.duration_minutes <= 240:
            errors["duration_minutes"] = _("Interview duration must be between 15 and 240 minutes.")
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"Interview for application {self.application_id}"

