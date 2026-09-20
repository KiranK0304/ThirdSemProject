from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Notification, NotificationType


@admin.action(description=_("Mark selected notifications as read"))
def mark_as_read(modeladmin, request, queryset):
    queryset.update(is_read=True)


@admin.action(description=_("Mark selected notifications as unread"))
def mark_as_unread(modeladmin, request, queryset):
    queryset.update(is_read=False)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "recipient_email",
        "type_badge",
        "title",
        "is_read_badge",
        "created_at",
    ]
    list_filter = ["notification_type", "is_read", "created_at"]
    search_fields = ["recipient__email", "recipient__name", "title", "message"]
    list_select_related = ["recipient"]
    autocomplete_fields = ["recipient"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    actions = [mark_as_read, mark_as_unread]

    @admin.display(description=_("Recipient"), ordering="recipient__email")
    def recipient_email(self, obj):
        return obj.recipient.email

    @admin.display(description=_("Notification Type"), ordering="notification_type")
    def type_badge(self, obj):
        colors = {
            NotificationType.EMPLOYER_APPROVED: ("#10b981", "#d1fae5"),
            NotificationType.EMPLOYER_REJECTED: ("#ef4444", "#fee2e2"),
            NotificationType.APPLICATION_SUBMITTED: ("#3b82f6", "#dbeafe"),
            NotificationType.APPLICATION_STATUS_CHANGED: ("#8b5cf6", "#ede9fe"),
        }
        fg, bg = colors.get(obj.notification_type, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_notification_type_display(),
        )

    @admin.display(description=_("Read"), ordering="is_read", boolean=True)
    def is_read_badge(self, obj):
        return obj.is_read
