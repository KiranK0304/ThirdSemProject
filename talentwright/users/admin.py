from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from talentwright.notifications.services import notify_employer_approved, notify_employer_rejected

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import EmployerProfile, Resume, SeekerProfile, User, VerificationStatus


class ResumeInline(admin.TabularInline):
    model = Resume
    extra = 0
    fields = ["title", "file_link", "is_primary", "created_at"]
    readonly_fields = ["file_link", "created_at"]

    @admin.display(description=_("Resume File"))
    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; font-weight: 500;">📄 View / Download</a>',
                obj.file.url,
            )
        return "-"


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["email", "name", "role_badge", "is_staff", "is_active", "date_joined"]
    list_filter = ["is_staff", "is_active", "is_superuser", "date_joined"]
    search_fields = ["email", "name"]
    ordering = ["-date_joined"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    @admin.display(description=_("Role"))
    def role_badge(self, obj):
        if obj.is_superuser:
            return format_html('<span style="background-color: #ef4444; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">Superuser</span>')
        if obj.is_staff:
            return format_html('<span style="background-color: #8b5cf6; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">Staff</span>')
        if obj.is_employer:
            return format_html('<span style="background-color: #3b82f6; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">Employer</span>')
        if obj.is_seeker:
            return format_html('<span style="background-color: #10b981; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">Seeker</span>')
        return format_html('<span style="background-color: #6b7280; color: white; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600;">User</span>')


@admin.action(description=_("Approve selected employers"))
def approve_employers(modeladmin, request, queryset):
    for profile in queryset:
        if profile.verification_status != VerificationStatus.APPROVED:
            profile.verification_status = VerificationStatus.APPROVED
            profile.save(update_fields=["verification_status", "updated_at"])
            notify_employer_approved(profile)


@admin.action(description=_("Reject selected employers"))
def reject_employers(modeladmin, request, queryset):
    for profile in queryset:
        if profile.verification_status != VerificationStatus.REJECTED:
            profile.verification_status = VerificationStatus.REJECTED
            profile.save(update_fields=["verification_status", "updated_at"])
            notify_employer_rejected(profile)


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ["user_email", "company_name", "verification_badge", "job_count", "created_at"]
    list_filter = ["verification_status", "created_at"]
    search_fields = ["user__email", "user__name", "company_name"]
    list_select_related = ["user"]
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "updated_at", "job_count"]
    actions = [approve_employers, reject_employers]

    @admin.display(description=_("User Email"), ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description=_("Verification Status"), ordering="verification_status")
    def verification_badge(self, obj):
        status = obj.verification_status
        colors = {
            VerificationStatus.APPROVED: ("#10b981", "#d1fae5"),
            VerificationStatus.PENDING: ("#f59e0b", "#fef3c7"),
            VerificationStatus.REJECTED: ("#ef4444", "#fee2e2"),
        }
        fg, bg = colors.get(status, ("#6b7280", "#f3f4f6"))
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 3px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600;">{}</span>',
            bg,
            fg,
            obj.get_verification_status_display(),
        )

    @admin.display(description=_("Jobs Posted"))
    def job_count(self, obj):
        return obj.jobs.count()


@admin.register(SeekerProfile)
class SeekerProfileAdmin(admin.ModelAdmin):
    list_display = ["user_email", "user_name", "phone", "resume_count", "application_count", "created_at"]
    search_fields = ["user__email", "user__name", "phone"]
    list_select_related = ["user"]
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "updated_at", "resume_count", "application_count"]
    inlines = [ResumeInline]

    @admin.display(description=_("User Email"), ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description=_("Name"), ordering="user__name")
    def user_name(self, obj):
        return obj.user.name or "-"

    @admin.display(description=_("Resumes"))
    def resume_count(self, obj):
        return obj.resumes.count()

    @admin.display(description=_("Applications"))
    def application_count(self, obj):
        return obj.applications.count()


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["title", "seeker_email", "file_link", "is_primary_badge", "created_at"]
    list_filter = ["is_primary", "created_at"]
    search_fields = ["title", "seeker__user__email", "seeker__user__name"]
    list_select_related = ["seeker__user"]
    autocomplete_fields = ["seeker"]
    readonly_fields = ["created_at", "updated_at", "file_link"]
    date_hierarchy = "created_at"

    @admin.display(description=_("Seeker Email"), ordering="seeker__user__email")
    def seeker_email(self, obj):
        return obj.seeker.user.email

    @admin.display(description=_("Resume File"))
    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer" style="color: #4f46e5; font-weight: 600;">📥 Download PDF</a>',
                obj.file.url,
            )
        return "-"

    @admin.display(description=_("Primary"), ordering="is_primary", boolean=True)
    def is_primary_badge(self, obj):
        return obj.is_primary
