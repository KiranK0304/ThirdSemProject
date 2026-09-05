"""URL configuration for recruiter_copilot API endpoints."""

from django.urls import path

from talentwright.recruiter_copilot.api.views import JobSessionListCreateView
from talentwright.recruiter_copilot.api.views import SessionMessageListCreateView

app_name = "recruiter_copilot"

urlpatterns = [
    path(
        "jobs/<int:job_id>/sessions/",
        JobSessionListCreateView.as_view(),
        name="job-sessions",
    ),
    path(
        "sessions/<int:session_id>/messages/",
        SessionMessageListCreateView.as_view(),
        name="session-messages",
    ),
]
