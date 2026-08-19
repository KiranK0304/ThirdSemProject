from django.contrib import admin

from talentwright.message.models import ChatRequest
from talentwright.message.models import Message


@admin.register(ChatRequest)
class ChatRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "seeker", "employer", "status", "created_at", "updated_at"]
    list_filter = ["status", "created_at"]
    search_fields = [
        "seeker__user__email",
        "seeker__user__name",
        "employer__user__email",
        "employer__company_name",
    ]
    ordering = ["-created_at"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "chat_request", "sender", "is_read", "created_at"]
    list_filter = ["is_read", "created_at"]
    search_fields = ["content", "sender__email", "sender__name"]
    ordering = ["-created_at"]
