from django.urls import path

from talentwright.applications.api.views import EmployerApplicationStatusUpdateView
from talentwright.applications.api.views import EmployerApplicationsListView
from talentwright.applications.api.views import EmployerInterviewCreateView
from talentwright.applications.api.views import EmployerInterviewListView
from talentwright.applications.api.views import EmployerInterviewUpdateView
from talentwright.applications.api.views import JobApplicationCreateView
from talentwright.applications.api.views import JobApplicationsListView
from talentwright.applications.api.views import SeekerApplicationDetailView
from talentwright.applications.api.views import SeekerApplicationsListView
from talentwright.applications.api.views import SeekerInterviewListView

app_name = "applications"

urlpatterns = [
    path("jobs/<int:job_id>/apply/", JobApplicationCreateView.as_view(), name="job-apply"),
    path("jobs/<int:job_id>/applications/", JobApplicationsListView.as_view(), name="job-applications"),
    path("employer/applications/", EmployerApplicationsListView.as_view(), name="employer-applications"),
    path("employer/interviews/", EmployerInterviewListView.as_view(), name="employer-interviews"),
    path(
        "employer/interviews/<int:pk>/",
        EmployerInterviewUpdateView.as_view(),
        name="employer-interview-update",
    ),
    path(
        "employer/applications/<int:application_id>/interview/",
        EmployerInterviewCreateView.as_view(),
        name="employer-interview-create",
    ),
    path(
        "employer/applications/<int:pk>/status/",
        EmployerApplicationStatusUpdateView.as_view(),
        name="employer-application-status-update",
    ),
    path("seeker/applications/", SeekerApplicationsListView.as_view(), name="seeker-applications"),
    path("seeker/applications/<int:pk>/", SeekerApplicationDetailView.as_view(), name="seeker-application-detail"),
    path("seeker/interviews/", SeekerInterviewListView.as_view(), name="seeker-interviews"),
]


