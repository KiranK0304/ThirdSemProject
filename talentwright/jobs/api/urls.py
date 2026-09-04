from django.urls import path

from talentwright.jobs.api.views import (
    JobAlertDetailView,
    JobAlertListCreateView,
    JobAlertMatchesListView,
    JobCreateView,
    JobDetailView,
    PublicJobDetailView,
    PublicJobListView,
    SavedJobCreateDeleteView,
    SavedJobListView,
    SeekerBookmarkListView,
    SeekerBookmarkView,
    SeekerRecommendedJobListView,
)

app_name = "jobs"

urlpatterns = [
    path("bookmarks/", SeekerBookmarkListView.as_view(), name="bookmarks"),
    path("recommendations/", SeekerRecommendedJobListView.as_view(), name="recommendations"),
    path("", PublicJobListView.as_view(), name="list"),
    path("<int:pk>/", PublicJobDetailView.as_view(), name="detail"),
    path("<int:job_id>/bookmark/", SeekerBookmarkView.as_view(), name="bookmark"),
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
