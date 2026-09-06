"""App configuration for candidate_rag."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CandidateRagConfig(AppConfig):
    name = "talentwright.candidate_rag"
    verbose_name = _("Candidate RAG")
