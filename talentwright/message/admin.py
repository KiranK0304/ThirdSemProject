from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from talentwright.message.models import ChatRequest, ChatRequestStatus, Message


@admin.action(description=_("Approve selected chat requests"))
def approve_chat_requests(modeladmin, request, queryset):
    queryset.update(status=ChatRequestStatus.APPROVED)


@admin.action(description=_("Reject selected chat requests"))
def reject_chat_requests(modeladmin, request, queryset):
    queryset.update(status=ChatRequestStatus.REJECTED)


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ["sender", "content_preview", "is_read", "created_at"]
    readonly_fields = ["sender", "content_preview", "is_read", "created_at"]
    can_delete = True

    @admin.display(description=_("Message Content"))
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content


@admin.register(ChatRequest)
class ChatRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "seeker_info",
        "employer_info",
        "status_badge",
        "message_count",
        "created_at",
        "updated_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "seeker__user__email",
        "seeker__user__name",
        "employer__user__email",
        "employer__company_name",
        "initial_message",
    ]
    list_select_related = [
        "seeker__user",
        "employer__user",
    ]
    autocomplete_fields = ["seeker", "employer"]
    readonly_fields = ["created_at", "updated_at", "message_count"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    actions = [approve_chat_requests, reject_chat_requests]
    inlines = [MessageInline]
    fieldsets = (
        (
            _("Connection Details"),
            {
                "fields": (
                    ("seeker", "employer"),
                    "status",
                    "initial_message",
                ),
            },
        ),
        (
            _("Activity"),
            {
                "fields": ("message_count", "created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description=_("Job Seeker"), ordering="seeker__user__email")
    def seeker_info(self, obj):
        name = obj.seeker.user.name or "Unnamed"
        email = obj.seeker.user.email
        return format_html('<div><strong>{}</strong><br><span style="color: #64748b; font-size: 11px;">{}</span></div>', name, email)

    @admin.display(description=_("Employer"), ordering="employer__company_name")
    def employer_info(self, obj):
        company = obj.employer.company_name or "Unnamed Company"
        email = obj.employer.user.email
        return format_html('<div><strong>{}</strong><br><span style="color: #64748b; font-size: 11px;">{}</span></div>', company, email)

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            ChatRequestStatus.APPROVED: ("#10b981", "#d1fae5"),
            ChatRequestStatus.PENDING: ("#f59e0b", "#fef3c7"),
            ChatRequestStatus.REJECTED: ("#ef4444", "#fee2e2"),
        }
        fg, bg = colors.get(obj.status, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_status_display(),
        )

    @admin.display(description=_("Messages"))
    def message_count(self, obj):
        return obj.messages.count()


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "chat_request", "sender_email", "content_preview", "is_read_badge", "created_at"]
    list_filter = ["is_read", "created_at"]
    search_fields = ["content", "sender__email", "sender__name"]
    list_select_related = ["chat_request", "sender"]
    autocomplete_fields = ["chat_request", "sender"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    @admin.display(description=_("Sender"), ordering="sender__email")
    def sender_email(self, obj):
        return obj.sender.email

    @admin.display(description=_("Content"))
    def content_preview(self, obj):
        return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content

    @admin.display(description=_("Read"), ordering="is_read", boolean=True)
    def is_read_badge(self, obj):
        return obj.is_read
