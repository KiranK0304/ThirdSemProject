from django.urls import path

from talentwright.applications.api.views import (
    EmployerApplicantCsvExportView,
    EmployerApplicationsListView,
    EmployerApplicationStatusUpdateView,
    EmployerInterviewCreateView,
    EmployerInterviewListView,
    EmployerInterviewUpdateView,
    EmployerJobOfferCreateUpdateView,
    EmployerRecruitmentAnalyticsView,
    JobApplicationCreateView,
    JobApplicationsListView,
    SeekerApplicationDetailView,
    SeekerApplicationsListView,
    SeekerInterviewListView,
    SeekerJobOfferDecisionView,
)

app_name = "applications"

urlpatterns = [
    path("employer/analytics/", EmployerRecruitmentAnalyticsView.as_view(), name="employer-recruitment-analytics"),
    path("employer/export/csv/", EmployerApplicantCsvExportView.as_view(), name="employer-applicant-csv-export"),
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
        "employer/applications/<int:application_id>/offer/",
        EmployerJobOfferCreateUpdateView.as_view(),
        name="employer-job-offer",
    ),
    path(
        "employer/applications/<int:pk>/status/",
        EmployerApplicationStatusUpdateView.as_view(),
        name="employer-application-status-update",
    ),
    path("seeker/applications/", SeekerApplicationsListView.as_view(), name="seeker-applications"),
    path("seeker/applications/<int:pk>/", SeekerApplicationDetailView.as_view(), name="seeker-application-detail"),
    path(
        "seeker/applications/<int:application_id>/offer/decision/",
        SeekerJobOfferDecisionView.as_view(),
        name="seeker-job-offer-decision",
    ),
    path("seeker/interviews/", SeekerInterviewListView.as_view(), name="seeker-interviews"),
]
