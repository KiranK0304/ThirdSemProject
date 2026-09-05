

from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    CASCADE,
    BooleanField,
    CharField,
    DateTimeField,
    EmailField,
    FileField,
    ForeignKey,
    OneToOneField,
    TextChoices,
    TextField,
    URLField,
)
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class VerificationStatus(TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class User(AbstractUser):
    """
    Default custom user model for Talentwright.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    @property
    def account_type(self) -> str | None:
        if hasattr(self, "employer_profile"):
            return "EMPLOYER"
        if hasattr(self, "seeker_profile"):
            return "SEEKER"
        return None

    @property
    def is_employer(self) -> bool:
        return hasattr(self, "employer_profile")

    @property
    def is_seeker(self) -> bool:
        return hasattr(self, "seeker_profile")


class EmployerProfile(models.Model):
    """
    Profile model for Employer accounts.
    """
    user = OneToOneField(User, on_delete=models.CASCADE, related_name="employer_profile")
    company_name = CharField(_("Company Name"), max_length=255, blank=True)
    website = URLField(_("Company Website"), blank=True)
    description = TextField(_("Company Description"), blank=True)
    verification_status = CharField(
        _("Verification Status"),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"EmployerProfile for {self.user.email} ({self.company_name or 'No Company Name'})"


class SeekerProfile(models.Model):
    """
    Profile model for Seeker accounts.
    """
    user = OneToOneField(User, on_delete=models.CASCADE, related_name="seeker_profile")
    phone = CharField(_("Phone Number"), max_length=30, blank=True)
    bio = TextField(_("Bio"), blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"SeekerProfile for {self.user.email}"


class Resume(models.Model):
    """
    Uploaded resume documents for a job seeker (maximum 3 per seeker).
    """
    seeker = ForeignKey(
        SeekerProfile,
        on_delete=CASCADE,
        related_name="resumes",
    )
    title = CharField(_("Resume Title"), max_length=255, blank=True)
    file = FileField(_("Resume File"), upload_to="resumes/%Y/%m/")
    is_primary = BooleanField(_("Is Primary"), default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "-created_at"]

    def clean(self):
        super().clean()
        if not self.pk and self.seeker_id:
            if self.seeker.resumes.count() >= 3:
                raise ValidationError({"seeker": _("A seeker can have a maximum of 3 resumes.")})

    def save(self, *args, **kwargs):
        if not self.title and self.file:
            self.title = self.file.name.split("/")[-1]

        # Automatically mark as primary if it's the seeker's first resume
        if self.seeker_id and not self.pk:
            if not Resume.objects.filter(seeker_id=self.seeker_id).exists():
                self.is_primary = True

        super().save(*args, **kwargs)

        # If this resume is set as primary, unmark other resumes for this seeker
        if self.is_primary and self.seeker_id:
            Resume.objects.filter(seeker_id=self.seeker_id).exclude(pk=self.pk).update(is_primary=False)

    def delete(self, *args, **kwargs):
        was_primary = self.is_primary
        seeker_id = self.seeker_id
        super().delete(*args, **kwargs)
        if was_primary and seeker_id:
            remaining = Resume.objects.filter(seeker_id=seeker_id).order_by("-created_at").first()
            if remaining:
                remaining.is_primary = True
                remaining.save(update_fields=["is_primary"])

    def __str__(self) -> str:
        return f"{self.title or self.file.name} ({self.seeker.user.email}){' [PRIMARY]' if self.is_primary else ''}"


