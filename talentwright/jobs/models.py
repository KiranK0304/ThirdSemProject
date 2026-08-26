from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CASCADE
from django.db.models import CharField
from django.db.models import CheckConstraint
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import ForeignKey
from django.db.models import Q
from django.db.models import TextChoices
from django.db.models import TextField
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _

from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile


ALERT_CRITERIA_ERROR = _(
    "Provide at least one of keyword, location, employment type, or minimum salary."
)


class EmploymentType(TextChoices):
    FULL_TIME = "FULL_TIME", _("Full time")
    PART_TIME = "PART_TIME", _("Part time")
    CONTRACT = "CONTRACT", _("Contract")
    INTERNSHIP = "INTERNSHIP", _("Internship")
    TEMPORARY = "TEMPORARY", _("Temporary")
    FREELANCE = "FREELANCE", _("Freelance")


class JobStatus(TextChoices):
    DRAFT = "DRAFT", _("Draft")
    OPEN = "OPEN", _("Open")
    CLOSED = "CLOSED", _("Closed")
    ARCHIVED = "ARCHIVED", _("Archived")


class Job(models.Model):
    employer = ForeignKey(
        EmployerProfile,
        on_delete=CASCADE,
        related_name="jobs",
    )
    title = CharField(_("Job title"), max_length=255)
    description = TextField(_("Job description"))
    location = CharField(_("Location"), max_length=255, blank=True)
    employment_type = CharField(
        _("Employment type"),
        max_length=20,
        choices=EmploymentType.choices,
    )
    salary_min = DecimalField(_("Minimum salary"), max_digits=12, decimal_places=2, null=True, blank=True)
    salary_max = DecimalField(_("Maximum salary"), max_digits=12, decimal_places=2, null=True, blank=True)
    salary_currency = CharField(_("Salary currency"), max_length=3, default="USD")
    status = CharField(
        _("Status"),
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.OPEN,
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employer", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            CheckConstraint(
                name="jobs_job_salary_range_valid",
                condition=Q(salary_min__isnull=True) | Q(salary_max__isnull=True) | Q(salary_min__lte=models.F("salary_max")),
            ),
        ]

    def clean(self):
        super().clean()
        if self.salary_min is not None and self.salary_max is not None and self.salary_min > self.salary_max:
            raise ValidationError({"salary_max": _("Maximum salary must be greater than or equal to minimum salary.")})

    def __str__(self) -> str:
        return f"{self.title} @ {self.employer.company_name or self.employer.user.email}"


class SavedJob(models.Model):
    """A job bookmarked by a seeker."""

    seeker = ForeignKey(SeekerProfile, on_delete=CASCADE, related_name="saved_jobs")
    job = ForeignKey(Job, on_delete=CASCADE, related_name="saved_by")
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            UniqueConstraint(
                fields=["seeker", "job"],
                name="jobs_saved_job_seeker_job_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.seeker.user.email} saved {self.job}"


class JobBookmark(models.Model):
    seeker = ForeignKey(
        SeekerProfile,
        on_delete=CASCADE,
        related_name="job_bookmarks",
    )
    job = ForeignKey(
        Job,
        on_delete=CASCADE,
        related_name="bookmarks",
    )
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            UniqueConstraint(fields=["seeker", "job"], name="jobs_jobbookmark_seeker_job_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.seeker.user.email} bookmarked {self.job.title}"


class AlertFrequency(TextChoices):
    DAILY = "DAILY", _("Daily")
    WEEKLY = "WEEKLY", _("Weekly")


class JobAlert(models.Model):
    """A saved job-search preference for a seeker."""

    seeker = ForeignKey(SeekerProfile, on_delete=CASCADE, related_name="job_alerts")
    keyword = CharField(_("Keyword"), max_length=255, blank=True)
    location = CharField(_("Location"), max_length=255, blank=True)
    employment_type = CharField(
        _("Employment type"),
        max_length=20,
        choices=EmploymentType.choices,
        blank=True,
    )
    minimum_salary = DecimalField(
        _("Minimum salary"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    frequency = CharField(
        _("Alert frequency"),
        max_length=10,
        choices=AlertFrequency.choices,
        default=AlertFrequency.DAILY,
    )
    is_active = models.BooleanField(_("Is active"), default=True)
    last_sent_at = DateTimeField(_("Last sent at"), null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["seeker", "is_active"])]

    def clean(self):
        super().clean()
        has_criteria = any(
            [
                self.keyword.strip(),
                self.location.strip(),
                self.employment_type,
                self.minimum_salary is not None,
            ]
        )
        if not has_criteria:
            raise ValidationError(ALERT_CRITERIA_ERROR)

    def __str__(self) -> str:
        return f"Job alert for {self.seeker.user.email}"

