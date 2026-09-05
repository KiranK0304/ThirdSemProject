"""Django app configuration for resume screening."""
from django.apps import AppConfig


class ResumeScreeningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "talentwright.resume_screening"
    verbose_name = "Resume Screening"
