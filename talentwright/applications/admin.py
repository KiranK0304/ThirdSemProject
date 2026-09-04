from django.contrib import admin

from talentwright.applications.models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["job", "seeker", "status", "created_at", "updated_at"]
    list_filter = ["status", "created_at", "updated_at"]
    search_fields = ["job__title", "seeker__user__email", "seeker__user__name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

