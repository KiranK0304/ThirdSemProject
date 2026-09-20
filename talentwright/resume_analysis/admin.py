"""Admin configuration for resume_analysis app."""

import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from talentwright.resume_analysis.models import AnalysisStatus, ResumeAnalysisRecord


@admin.action(description=_("Reset status to Pending (re-queue)"))
def reset_to_pending(modeladmin, request, queryset):
    queryset.update(status=AnalysisStatus.PENDING, error_message="")


@admin.register(ResumeAnalysisRecord)
class ResumeAnalysisRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "candidate_name",
        "job_title",
        "status_badge",
        "score_badge",
        "recommendation_badge",
        "created_at",
    ]
    list_filter = ["status", "recommendation", "created_at"]
    search_fields = [
        "application__seeker__user__email",
        "application__seeker__user__name",
        "application__job__title",
        "recommendation",
    ]
    list_select_related = [
        "application__seeker__user",
        "application__job",
        "application__job__employer",
    ]
    autocomplete_fields = ["application"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "formatted_scorecard",
        "formatted_structured_resume",
        "raw_text_preview",
    ]
    date_hierarchy = "created_at"
    actions = [reset_to_pending]
    fieldsets = (
        (
            _("Screening Overview"),
            {
                "fields": (
                    "application",
                    ("status", "overall_score", "recommendation"),
                    "error_message",
                ),
            },
        ),
        (
            _("Evaluation Scorecard"),
            {
                "classes": ("collapse",),
                "fields": ("formatted_scorecard", "evaluation_scorecard"),
            },
        ),
        (
            _("Structured Resume"),
            {
                "classes": ("collapse",),
                "fields": ("formatted_structured_resume", "structured_resume"),
            },
        ),
        (
            _("Raw Extracted Text"),
            {
                "classes": ("collapse",),
                "fields": ("raw_text_preview", "raw_text"),
            },
        ),
        (
            _("Audit Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description=_("Candidate"), ordering="application__seeker__user__email")
    def candidate_name(self, obj):
        name = obj.application.seeker.user.name or "Unnamed"
        email = obj.application.seeker.user.email
        return format_html('<div><strong>{}</strong><br><span style="color: #64748b; font-size: 11px;">{}</span></div>', name, email)

    @admin.display(description=_("Job Posting"), ordering="application__job__title")
    def job_title(self, obj):
        return obj.application.job.title

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            AnalysisStatus.COMPLETED: ("#10b981", "#d1fae5"),
            AnalysisStatus.PROCESSING: ("#3b82f6", "#dbeafe"),
            AnalysisStatus.PENDING: ("#f59e0b", "#fef3c7"),
            AnalysisStatus.FAILED: ("#ef4444", "#fee2e2"),
        }
        fg, bg = colors.get(obj.status, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_status_display(),
        )

    @admin.display(description=_("Score"), ordering="overall_score")
    def score_badge(self, obj):
        if obj.overall_score is None:
            return "-"
        score = float(obj.overall_score)
        if score >= 75:
            color, bg = "#10b981", "#d1fae5"
        elif score >= 50:
            color, bg = "#f59e0b", "#fef3c7"
        else:
            color, bg = "#ef4444", "#fee2e2"
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 6px; font-size: 12px; font-weight: 700;">{:.1f} / 100</span>',
            bg,
            color,
            score,
        )

    @admin.display(description=_("Recommendation"), ordering="recommendation")
    def recommendation_badge(self, obj):
        if not obj.recommendation:
            return "-"
        rec = obj.recommendation.upper()
        if "STRONG" in rec:
            color, bg = "#10b981", "#d1fae5"
        elif "MODERATE" in rec:
            color, bg = "#3b82f6", "#dbeafe"
        elif "WEAK" in rec:
            color, bg = "#f59e0b", "#fef3c7"
        else:
            color, bg = "#6b7280", "#f3f4f6"
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;">{}</span>',
            bg,
            color,
            obj.recommendation,
        )

    @admin.display(description=_("Scorecard Preview"))
    def formatted_scorecard(self, obj):
        if not obj.evaluation_scorecard:
            return _("No scorecard data recorded.")
        formatted = json.dumps(obj.evaluation_scorecard, indent=2)
        return format_html(
            '<pre style="background: #1e293b; color: #f8fafc; padding: 12px; border-radius: 8px; max-height: 350px; overflow-y: auto; font-size: 12px;">{}</pre>',
            formatted,
        )

    @admin.display(description=_("Structured Resume Preview"))
    def formatted_structured_resume(self, obj):
        if not obj.structured_resume:
            return _("No structured resume data.")
        formatted = json.dumps(obj.structured_resume, indent=2)
        return format_html(
            '<pre style="background: #1e293b; color: #f8fafc; padding: 12px; border-radius: 8px; max-height: 350px; overflow-y: auto; font-size: 12px;">{}</pre>',
            formatted,
        )

    @admin.display(description=_("Raw Text Preview"))
    def raw_text_preview(self, obj):
        if not obj.raw_text:
            return _("No raw text available.")
        return format_html(
            '<pre style="background: #f8fafc; border: 1px solid #e2e8f0; color: #334155; padding: 12px; border-radius: 8px; max-height: 250px; overflow-y: auto; white-space: pre-wrap; font-size: 12px;">{}</pre>',
            obj.raw_text[:2000] + ("..." if len(obj.raw_text) > 2000 else ""),
        )
