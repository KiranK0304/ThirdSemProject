from django.db import models
from django.utils.translation import gettext_lazy as _

from talentwright.jobs.models import Job
from talentwright.users.models import SeekerProfile


class ApplicationStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", _("Submitted")
    UNDER_REVIEW = "UNDER_REVIEW", _("Under review")
    SHORTLISTED = "SHORTLISTED", _("Shortlisted")
    REJECTED = "REJECTED", _("Rejected")
    WITHDRAWN = "WITHDRAWN", _("Withdrawn")


class Application(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    seeker = models.ForeignKey(SeekerProfile, on_delete=models.CASCADE, related_name="applications")
    cover_letter = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.SUBMITTED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["job", "seeker"], name="applications_unique_job_seeker"),
        ]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["seeker", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.seeker.user.email} - {self.job.title}"
