"""Admin configuration for candidate_rag models."""

from django.contrib import admin

from talentwright.candidate_rag.models import CandidateResumeChunk


@admin.register(CandidateResumeChunk)
class CandidateResumeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "candidate_name",
        "chunk_type",
        "job",
        "application",
        "created_at",
    )
    list_filter = ("chunk_type", "job")
    search_fields = ("candidate_name", "content")
    readonly_fields = ("created_at", "updated_at")
