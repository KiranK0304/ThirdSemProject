from django.db.models import Q

from talentwright.jobs.models import Job
from talentwright.jobs.models import JobAlert
from talentwright.jobs.models import JobStatus
from talentwright.users.models import VerificationStatus


def matching_jobs_for_alert(alert: JobAlert):
    """Return public, open jobs matching an alert's saved search criteria."""
    queryset = Job.objects.select_related("employer", "employer__user").filter(
        status=JobStatus.OPEN,
        employer__verification_status=VerificationStatus.APPROVED,
    )

    if alert.keyword:
        queryset = queryset.filter(
            Q(title__icontains=alert.keyword)
            | Q(description__icontains=alert.keyword)
            | Q(location__icontains=alert.keyword)
            | Q(employer__company_name__icontains=alert.keyword),
        )
    if alert.location:
        queryset = queryset.filter(location__icontains=alert.location)
    if alert.employment_type:
        queryset = queryset.filter(employment_type=alert.employment_type)
    if alert.minimum_salary is not None:
        queryset = queryset.filter(salary_max__gte=alert.minimum_salary)

    return queryset
