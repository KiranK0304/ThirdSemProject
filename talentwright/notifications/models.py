from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class NotificationType(models.TextChoices):
    EMPLOYER_APPROVED = "EMPLOYER_APPROVED", _("Employer approved")
    EMPLOYER_REJECTED = "EMPLOYER_REJECTED", _("Employer rejected")
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED", _("Application submitted")
    APPLICATION_STATUS_CHANGED = "APPLICATION_STATUS_CHANGED", _("Application status changed")


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=40, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_url = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} for {self.recipient.email}"
