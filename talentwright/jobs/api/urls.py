from django.urls import path

from talentwright.jobs.api.views import JobAlertDetailView
from talentwright.jobs.api.views import JobAlertListCreateView
from talentwright.jobs.api.views import JobAlertMatchesListView
from talentwright.jobs.api.views import JobCreateView
from talentwright.jobs.api.views import JobDetailView
from talentwright.jobs.api.views import PublicJobDetailView
from talentwright.jobs.api.views import PublicJobListView
from talentwright.jobs.api.views import SavedJobCreateDeleteView
from talentwright.jobs.api.views import SavedJobListView

app_name = "jobs"

urlpatterns = [
    path("", PublicJobListView.as_view(), name="list"),
    path("<int:pk>/", PublicJobDetailView.as_view(), name="detail"),
    path("manage/", JobCreateView.as_view(), name="manage-list"),
    path("manage/<int:pk>/", JobDetailView.as_view(), name="manage-detail"),
    path("saved/", SavedJobListView.as_view(), name="saved-list"),
    path(
        "<int:job_id>/save/",
        SavedJobCreateDeleteView.as_view(),
        name="saved-create-delete",
    ),
    path("alerts/", JobAlertListCreateView.as_view(), name="alert-list"),
    path("alerts/<int:pk>/", JobAlertDetailView.as_view(), name="alert-detail"),
    path(
        "alerts/<int:pk>/matches/",
        JobAlertMatchesListView.as_view(),
        name="alert-matches",
    ),
]
