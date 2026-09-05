"""URL patterns for resume screening API."""
from django.urls import path

from talentwright.resume_screening.api.views import JobScreeningPrepareView

app_name = "resume_screening"

urlpatterns = [
    path(
        "jobs/<int:job_id>/prepare/",
        JobScreeningPrepareView.as_view(),
        name="job-screening-prepare",
    ),
]
