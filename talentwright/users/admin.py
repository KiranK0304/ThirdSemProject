from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import EmployerProfile, SeekerProfile, User, VerificationStatus
from talentwright.notifications.services import notify_employer_approved, notify_employer_rejected


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
    list_display = ["email", "name", "is_superuser"]
    search_fields = ["name"]
    ordering = ["id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


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
    list_display = ["user", "company_name", "verification_status", "created_at"]
    list_filter = ["verification_status", "created_at"]
    search_fields = ["user__email", "company_name"]
    actions = [approve_employers, reject_employers]


@admin.register(SeekerProfile)
class SeekerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "created_at"]
    search_fields = ["user__email", "phone"]

