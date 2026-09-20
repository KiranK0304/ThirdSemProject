"""Admin configuration for recruiter_copilot app."""

import json

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from talentwright.recruiter_copilot.models import CopilotMessage, CopilotSession, MessageRole


class CopilotMessageInline(admin.TabularInline):
    model = CopilotMessage
    extra = 0
    fields = ["role_badge", "content_preview", "created_at"]
    readonly_fields = ["role_badge", "content_preview", "created_at"]
    can_delete = True

    @admin.display(description=_("Role"))
    def role_badge(self, obj):
        colors = {
            MessageRole.USER: ("#3b82f6", "#dbeafe"),
            MessageRole.ASSISTANT: ("#10b981", "#d1fae5"),
            MessageRole.SYSTEM: ("#6b7280", "#f3f4f6"),
        }
        fg, bg = colors.get(obj.role, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_role_display(),
        )

    @admin.display(description=_("Content Snippet"))
    def content_preview(self, obj):
        snippet = obj.content[:120] + "..." if len(obj.content) > 120 else obj.content
        return snippet


@admin.register(CopilotSession)
class CopilotSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "title_display",
        "job_title",
        "employer_company",
        "message_count",
        "updated_at",
        "created_at",
    ]
    list_filter = ["created_at", "updated_at"]
    search_fields = [
        "title",
        "job__title",
        "employer__company_name",
        "employer__user__email",
    ]
    list_select_related = [
        "job",
        "employer",
        "employer__user",
    ]
    autocomplete_fields = ["job", "employer"]
    readonly_fields = ["created_at", "updated_at", "message_count"]
    date_hierarchy = "created_at"
    inlines = [CopilotMessageInline]

    @admin.display(description=_("Session Title"), ordering="title")
    def title_display(self, obj):
        return obj.title or f"Session #{obj.id}"

    @admin.display(description=_("Job Posting"), ordering="job__title")
    def job_title(self, obj):
        return obj.job.title

    @admin.display(description=_("Employer"), ordering="employer__company_name")
    def employer_company(self, obj):
        return obj.employer.company_name or obj.employer.user.email

    @admin.display(description=_("Messages"))
    def message_count(self, obj):
        return obj.messages.count()


@admin.register(CopilotMessage)
class CopilotMessageAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "session_title",
        "role_badge",
        "content_snippet",
        "created_at",
    ]
    list_filter = ["role", "created_at"]
    search_fields = [
        "content",
        "session__title",
        "session__job__title",
    ]
    list_select_related = ["session", "session__job"]
    autocomplete_fields = ["session"]
    readonly_fields = ["created_at", "metadata_preview"]
    date_hierarchy = "created_at"
    fieldsets = (
        (
            _("Message"),
            {
                "fields": ("session", "role", "content"),
            },
        ),
        (
            _("Metadata & Context"),
            {
                "classes": ("collapse",),
                "fields": ("metadata_preview", "metadata"),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at",),
            },
        ),
    )

    @admin.display(description=_("Session"), ordering="session__title")
    def session_title(self, obj):
        return obj.session.title or f"Session #{obj.session_id}"

    @admin.display(description=_("Role"), ordering="role")
    def role_badge(self, obj):
        colors = {
            MessageRole.USER: ("#3b82f6", "#dbeafe"),
            MessageRole.ASSISTANT: ("#10b981", "#d1fae5"),
            MessageRole.SYSTEM: ("#6b7280", "#f3f4f6"),
        }
        fg, bg = colors.get(obj.role, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_role_display(),
        )

    @admin.display(description=_("Content Snippet"))
    def content_snippet(self, obj):
        return obj.content[:150] + "..." if len(obj.content) > 150 else obj.content

    @admin.display(description=_("Metadata Preview"))
    def metadata_preview(self, obj):
        if not obj.metadata:
            return _("No metadata.")
        formatted = json.dumps(obj.metadata, indent=2)
        return format_html(
            '<pre style="background: #1e293b; color: #f8fafc; padding: 10px; border-radius: 6px; max-height: 250px; overflow-y: auto; font-size: 12px;">{}</pre>',
            formatted,
        )
