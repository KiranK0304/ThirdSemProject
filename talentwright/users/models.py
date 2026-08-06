

from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField, DateTimeField, EmailField, OneToOneField, TextChoices, TextField, URLField
from django.urls import reverse
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

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"pk": self.id})


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

