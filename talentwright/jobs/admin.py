from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from talentwright.jobs.models import EmploymentType, Job, JobAlert, JobBookmark, JobStatus, SavedJob


@admin.action(description=_("Mark selected jobs as Open"))
def mark_jobs_open(modeladmin, request, queryset):
    queryset.update(status=JobStatus.OPEN)


@admin.action(description=_("Mark selected jobs as Closed"))
def mark_jobs_closed(modeladmin, request, queryset):
    queryset.update(status=JobStatus.CLOSED)


@admin.action(description=_("Mark selected jobs as Archived"))
def mark_jobs_archived(modeladmin, request, queryset):
    queryset.update(status=JobStatus.ARCHIVED)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "employer_company",
        "status_badge",
        "employment_type_badge",
        "location",
        "salary_range_display",
        "applicant_count",
        "created_at",
    ]
    list_filter = ["status", "employment_type", "created_at"]
    search_fields = [
        "title",
        "description",
        "location",
        "employer__company_name",
        "employer__user__email",
    ]
    list_select_related = ["employer", "employer__user"]
    autocomplete_fields = ["employer"]
    readonly_fields = ["created_at", "updated_at", "applicant_count"]
    date_hierarchy = "created_at"
    actions = [mark_jobs_open, mark_jobs_closed, mark_jobs_archived]
    fieldsets = (
        (
            _("Job Details"),
            {
                "fields": (
                    "employer",
                    "title",
                    "status",
                    "employment_type",
                    "location",
                    "description",
                ),
            },
        ),
        (
            _("Compensation"),
            {
                "fields": (
                    ("salary_min", "salary_max", "salary_currency"),
                ),
            },
        ),
        (
            _("System Metadata"),
            {
                "fields": ("applicant_count", "created_at", "updated_at"),
            },
        ),
    )

    @admin.display(description=_("Employer"), ordering="employer__company_name")
    def employer_company(self, obj):
        return obj.employer.company_name or obj.employer.user.email

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colors = {
            JobStatus.OPEN: ("#10b981", "#d1fae5"),
            JobStatus.DRAFT: ("#6b7280", "#f3f4f6"),
            JobStatus.CLOSED: ("#ef4444", "#fee2e2"),
            JobStatus.ARCHIVED: ("#8b5cf6", "#ede9fe"),
        }
        fg, bg = colors.get(obj.status, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_status_display(),
        )

    @admin.display(description=_("Type"), ordering="employment_type")
    def employment_type_badge(self, obj):
        return format_html(
            '<span style="background-color: #f1f5f9; color: #334155; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 500;">{}</span>',
            obj.get_employment_type_display(),
        )

    @admin.display(description=_("Salary Range"))
    def salary_range_display(self, obj):
        if obj.salary_min and obj.salary_max:
            return f"{obj.salary_currency} {obj.salary_min:,.0f} - {obj.salary_max:,.0f}"
        if obj.salary_min:
            return f"From {obj.salary_currency} {obj.salary_min:,.0f}"
        if obj.salary_max:
            return f"Up to {obj.salary_currency} {obj.salary_max:,.0f}"
        return _("Not disclosed")

    @admin.display(description=_("Applicants"))
    def applicant_count(self, obj):
        return obj.applications.count()


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("seeker_email", "job_title", "created_at")
    list_select_related = ("seeker__user", "job", "job__employer")
    search_fields = ("seeker__user__email", "job__title", "job__employer__company_name")
    autocomplete_fields = ("seeker", "job")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"

    @admin.display(description=_("Seeker Email"), ordering="seeker__user__email")
    def seeker_email(self, obj):
        return obj.seeker.user.email

    @admin.display(description=_("Job Title"), ordering="job__title")
    def job_title(self, obj):
        return obj.job.title


@admin.register(JobBookmark)
class JobBookmarkAdmin(admin.ModelAdmin):
    list_display = ("seeker_email", "job_title", "created_at")
    list_select_related = ("seeker__user", "job", "job__employer")
    search_fields = ("seeker__user__email", "job__title", "job__employer__company_name")
    autocomplete_fields = ("seeker", "job")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"

    @admin.display(description=_("Seeker Email"), ordering="seeker__user__email")
    def seeker_email(self, obj):
        return obj.seeker.user.email

    @admin.display(description=_("Job Title"), ordering="job__title")
    def job_title(self, obj):
        return obj.job.title


@admin.register(JobAlert)
class JobAlertAdmin(admin.ModelAdmin):
    list_display = (
        "seeker_email",
        "keyword",
        "location",
        "frequency",
        "is_active_badge",
        "last_sent_at",
        "created_at",
    )
    list_filter = ("frequency", "is_active", "employment_type")
    list_select_related = ("seeker__user",)
    search_fields = ("seeker__user__email", "keyword", "location")
    autocomplete_fields = ("seeker",)
    readonly_fields = ("created_at", "updated_at", "last_sent_at")
    date_hierarchy = "created_at"

    @admin.display(description=_("Seeker Email"), ordering="seeker__user__email")
    def seeker_email(self, obj):
        return obj.seeker.user.email

    @admin.display(description=_("Active"), ordering="is_active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active
