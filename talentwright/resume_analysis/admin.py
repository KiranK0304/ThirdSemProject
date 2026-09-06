"""Admin configuration for resume_analysis app."""

from django.contrib import admin

from talentwright.resume_analysis.models import ResumeAnalysisRecord


@admin.register(ResumeAnalysisRecord)
class ResumeAnalysisRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "application",
        "status",
        "overall_score",
        "recommendation",
        "created_at",
    ]
    list_filter = ["status", "recommendation", "created_at"]
    search_fields = [
        "application__seeker__user__email",
        "application__job__title",
        "recommendation",
    ]
    readonly_fields = ["created_at", "updated_at"]
