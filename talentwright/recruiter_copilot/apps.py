"""App configuration for recruiter_copilot."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RecruiterCopilotConfig(AppConfig):
    name = "talentwright.recruiter_copilot"
    verbose_name = _("Recruiter Copilot")
