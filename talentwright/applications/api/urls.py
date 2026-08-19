from django.urls import path

from talentwright.applications.api.views import (
    EmployerApplicationListView,
    EmployerApplicationStatusView,
    JobApplicantListView,
    JobApplicationCreateView,
    SeekerApplicationDetailView,
    SeekerApplicationListView,
)

app_name = "applications"

urlpatterns = [
    path("jobs/<int:job_id>/apply/", JobApplicationCreateView.as_view(), name="apply"),
    path("seeker/applications/", SeekerApplicationListView.as_view(), name="seeker-list"),
    path("seeker/applications/<int:pk>/", SeekerApplicationDetailView.as_view(), name="seeker-detail"),
    path("employer/applications/", EmployerApplicationListView.as_view(), name="employer-list"),
    path("jobs/<int:job_id>/applications/", JobApplicantListView.as_view(), name="job-applicants"),
    path("employer/applications/<int:pk>/status/", EmployerApplicationStatusView.as_view(), name="status"),
]
