from django.urls import path

from talentwright.applications.api.views import EmployerApplicationsListView
from talentwright.applications.api.views import JobApplicationCreateView
from talentwright.applications.api.views import JobApplicationsListView

app_name = "applications"

urlpatterns = [
    path("jobs/<int:job_id>/apply/", JobApplicationCreateView.as_view(), name="job-apply"),
    path("jobs/<int:job_id>/applications/", JobApplicationsListView.as_view(), name="job-applications"),
    path("employer/applications/", EmployerApplicationsListView.as_view(), name="employer-applications"),
]
