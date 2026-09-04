from django.contrib import admin

from talentwright.jobs.models import JobAlert
from talentwright.jobs.models import SavedJob


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("seeker", "job", "created_at")
    list_select_related = ("seeker__user", "job")
    search_fields = ("seeker__user__email", "job__title")


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = (
        "seeker",
        "keyword",
        "location",
        "frequency",
        "is_active",
        "last_sent_at",
    )
    list_filter = ("frequency", "is_active", "employment_type")
    list_select_related = ("seeker__user",)
    search_fields = ("seeker__user__email", "keyword", "location")
