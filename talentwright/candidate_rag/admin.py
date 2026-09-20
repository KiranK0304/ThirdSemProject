"""Admin configuration for candidate_rag models."""

import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from talentwright.candidate_rag.models import CandidateResumeChunk, ChunkType


@admin.register(CandidateResumeChunk)
class CandidateResumeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "candidate_display",
        "chunk_type_badge",
        "job_title",
        "content_snippet",
        "created_at",
    )
    list_filter = ("chunk_type", "created_at")
    search_fields = ("candidate_name", "content", "job__title")
    list_select_related = ("job", "application", "application__seeker__user", "resume_analysis")
    autocomplete_fields = ["job", "application", "resume_analysis"]
    readonly_fields = ("created_at", "updated_at", "embedding_dimensions", "formatted_metadata")
    date_hierarchy = "created_at"
    fieldsets = (
        (
            _("Chunk Identification"),
            {
                "fields": (
                    ("candidate_name", "chunk_type"),
                    ("job", "application", "resume_analysis"),
                ),
            },
        ),
        (
            _("Text Content"),
            {
                "fields": ("content",),
            },
        ),
        (
            _("Vector & Metadata"),
            {
                "classes": ("collapse",),
                "fields": ("embedding_dimensions", "formatted_metadata", "metadata", "embedding"),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description=_("Candidate"), ordering="candidate_name")
    def candidate_display(self, obj):
        return obj.candidate_name or f"App #{obj.application_id}"

    @admin.display(description=_("Job Posting"), ordering="job__title")
    def job_title(self, obj):
        return obj.job.title

    @admin.display(description=_("Chunk Type"), ordering="chunk_type")
    def chunk_type_badge(self, obj):
        colors = {
            ChunkType.WORK_EXPERIENCE: ("#3b82f6", "#dbeafe"),
            ChunkType.SKILLS_SUMMARY: ("#10b981", "#d1fae5"),
            ChunkType.PROJECT: ("#8b5cf6", "#ede9fe"),
            ChunkType.EDUCATION_CERTIFICATIONS: ("#f59e0b", "#fef3c7"),
        }
        fg, bg = colors.get(obj.chunk_type, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_chunk_type_display(),
        )

    @admin.display(description=_("Content Snippet"))
    def content_snippet(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    @admin.display(description=_("Vector Dimension"))
    def embedding_dimensions(self, obj):
        dim = len(obj.embedding) if isinstance(obj.embedding, list) else 0
        return f"{dim} dimensions" if dim > 0 else _("No embedding generated")

    @admin.display(description=_("Metadata Preview"))
    def formatted_metadata(self, obj):
        if not obj.metadata:
            return _("No metadata.")
        formatted = json.dumps(obj.metadata, indent=2)
        return format_html(
            '<pre style="background: #1e293b; color: #f8fafc; padding: 10px; border-radius: 6px; max-height: 200px; overflow-y: auto; font-size: 12px;">{}</pre>',
            formatted,
        )
