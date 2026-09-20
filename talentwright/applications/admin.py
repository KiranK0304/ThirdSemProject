from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from talentwright.applications.models import Application, ApplicationStatus, Interview, InterviewStatus


@admin.action(description=_("Mark selected applications as Shortlisted"))
def mark_as_shortlisted(modeladmin, request, queryset):
    queryset.update(status=ApplicationStatus.SHORTLISTED)


@admin.action(description=_("Mark selected applications as Under Review"))
def mark_as_under_review(modeladmin, request, queryset):
    queryset.update(status=ApplicationStatus.UNDER_REVIEW)


@admin.action(description=_("Mark selected applications as Rejected"))
def mark_as_rejected(modeladmin, request, queryset):
    queryset.update(status=ApplicationStatus.REJECTED)


@admin.action(description=_("Mark selected interviews as Completed"))
def mark_interview_completed(modeladmin, request, queryset):
    queryset.update(status=InterviewStatus.COMPLETED)


@admin.action(description=_("Mark selected interviews as Cancelled"))
def mark_interview_cancelled(modeladmin, request, queryset):
    queryset.update(status=InterviewStatus.CANCELLED)


class InterviewInline(admin.StackedInline):
    model = Interview
    extra = 0
    fields = [
        ("scheduled_at", "duration_minutes", "status"),
        "meeting_url",
        "notes",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "candidate_info",
        "job_title",
        "status_badge",
        "ai_score_badge",
        "resume_link",
        "created_at",
    ]
    list_filter = ["status", "created_at", "updated_at"]
    search_fields = [
        "seeker__user__email",
        "seeker__user__name",
        "job__title",
        "job__employer__company_name",
    ]
    list_select_related = [
        "job",
        "job__employer",
        "seeker__user",
        "resume",
    ]
    autocomplete_fields = ["job", "seeker", "resume"]
    readonly_fields = ["created_at", "updated_at", "ai_score_badge", "resume_link"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    actions = [mark_as_shortlisted, mark_as_under_review, mark_as_rejected]
    inlines = [InterviewInline]
    fieldsets = (
        (
            _("Application Overview"),
            {
                "fields": (
                    ("job", "seeker"),
                    ("status", "resume"),
                    ("resume_link", "ai_score_badge"),
                ),
            },
        ),
        (
            _("Candidate Submission"),
            {
                "fields": ("cover_letter", "rejection_note"),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description=_("Candidate"), ordering="seeker__user__email")
    def candidate_info(self, obj):
        name = obj.seeker.user.name or "Unnamed"
        email = obj.seeker.user.email
        return format_html('<div><strong>{}</strong><br><span style="color: #64748b; font-size: 11px;">{}</span></div>', name, email)

    @admin.display(description=_("Job Posting"), ordering="job__title")
    def job_title(self, obj):
        company = obj.job.employer.company_name or "Unknown Company"
        return format_html('<div><strong>{}</strong><br><span style="color: #64748b; font-size: 11px;">{}</span></div>', obj.job.title, company)

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            ApplicationStatus.SUBMITTED: ("#3b82f6", "#dbeafe"),
            ApplicationStatus.UNDER_REVIEW: ("#f59e0b", "#fef3c7"),
            ApplicationStatus.SHORTLISTED: ("#10b981", "#d1fae5"),
            ApplicationStatus.OFFERED: ("#8b5cf6", "#ede9fe"),
            ApplicationStatus.REJECTED: ("#ef4444", "#fee2e2"),
            ApplicationStatus.WITHDRAWN: ("#6b7280", "#f3f4f6"),
        }
        fg, bg = colors.get(obj.status, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_status_display(),
        )

    @admin.display(description=_("AI Score"))
    def ai_score_badge(self, obj):
        try:
            record = getattr(obj, "resume_analysis", None)
            if record and record.overall_score is not None:
                score = record.overall_score
                if score >= 75:
                    color, bg = "#10b981", "#d1fae5"
                elif score >= 50:
                    color, bg = "#f59e0b", "#fef3c7"
                else:
                    color, bg = "#ef4444", "#fee2e2"
                return format_html(
                    '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;">{:.1f} / 100</span>',
                    bg,
                    color,
                    score,
                )
        except Exception:
            pass
        return format_html('<span style="color: #94a3b8; font-size: 11px;">Not scored</span>')

    @admin.display(description=_("Resume File"))
    def resume_link(self, obj):
        if obj.resume and obj.resume.file:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; font-weight: 600;">📄 View PDF</a>',
                obj.resume.file.url,
            )
        return "-"


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "candidate_info",
        "job_title",
        "scheduled_at",
        "duration_display",
        "status_badge",
        "meeting_link",
        "created_at",
    ]
    list_filter = ["status", "scheduled_at"]
    search_fields = [
        "application__seeker__user__email",
        "application__seeker__user__name",
        "application__job__title",
        "meeting_url",
    ]
    list_select_related = [
        "application__seeker__user",
        "application__job",
        "application__job__employer",
    ]
    autocomplete_fields = ["application"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "scheduled_at"
    actions = [mark_interview_completed, mark_interview_cancelled]

    @admin.display(description=_("Candidate"), ordering="application__seeker__user__email")
    def candidate_info(self, obj):
        name = obj.application.seeker.user.name or "Unnamed"
        email = obj.application.seeker.user.email
        return format_html('<div><strong>{}</strong><br><span style="color: #64748b; font-size: 11px;">{}</span></div>', name, email)

    @admin.display(description=_("Job Posting"), ordering="application__job__title")
    def job_title(self, obj):
        return obj.application.job.title

    @admin.display(description=_("Duration"))
    def duration_display(self, obj):
        return f"{obj.duration_minutes} min"

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            InterviewStatus.SCHEDULED: ("#3b82f6", "#dbeafe"),
            InterviewStatus.COMPLETED: ("#10b981", "#d1fae5"),
            InterviewStatus.CANCELLED: ("#ef4444", "#fee2e2"),
        }
        fg, bg = colors.get(obj.status, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_status_display(),
        )

    @admin.display(description=_("Meeting Link"))
    def meeting_link(self, obj):
        if obj.meeting_url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; font-weight: 600;">🔗 Join Meeting</a>',
                obj.meeting_url,
            )
        return "-"
