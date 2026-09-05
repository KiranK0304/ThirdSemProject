"""URL patterns for resume screening and candidate ranking API."""
from django.urls import path

from talentwright.resume_screening.api.views import (
    JobScreeningCopilotView,
    JobScreeningCriteriaView,
    JobScreeningPrepareView,
    JobScreeningRankView,
)

app_name = "resume_screening"

urlpatterns = [
    path(
        "jobs/<int:job_id>/prepare/",
        JobScreeningPrepareView.as_view(),
        name="job-screening-prepare",
    ),
    path(
        "jobs/<int:job_id>/criteria/",
        JobScreeningCriteriaView.as_view(),
        name="job-screening-criteria",
    ),
    path(
        "jobs/<int:job_id>/rank/",
        JobScreeningRankView.as_view(),
        name="job-screening-rank",
    ),
    path(
        "jobs/<int:job_id>/copilot/",
        JobScreeningCopilotView.as_view(),
        name="job-screening-copilot",
    ),
]
