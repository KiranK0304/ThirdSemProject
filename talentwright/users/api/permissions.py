from rest_framework.permissions import BasePermission

from talentwright.users.models import VerificationStatus


class IsAdmin(BasePermission):
    """
    Allows access only to admin users (staff or superuser).
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )


class IsEmployer(BasePermission):
    """
    Allows access only to authenticated users with an EmployerProfile.
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "employer_profile")
        )


class IsVerifiedEmployer(BasePermission):
    """
    Allows access only to authenticated employers whose verification status is APPROVED.
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "employer_profile")
            and request.user.employer_profile.verification_status == VerificationStatus.APPROVED
        )


class IsSeeker(BasePermission):
    """
    Allows access only to authenticated users with a SeekerProfile.
    """
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "seeker_profile")
        )
