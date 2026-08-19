from django.urls import path

from talentwright.jobs.api.views import JobCreateView
from talentwright.jobs.api.views import JobDetailView
from talentwright.jobs.api.views import PublicJobDetailView
from talentwright.jobs.api.views import PublicJobListView
from talentwright.jobs.api.views import SeekerRecommendedJobListView
from talentwright.jobs.api.views import SeekerBookmarkListView
from talentwright.jobs.api.views import SeekerBookmarkView

app_name = "jobs"

urlpatterns = [
    path("bookmarks/", SeekerBookmarkListView.as_view(), name="bookmarks"),
    path("recommendations/", SeekerRecommendedJobListView.as_view(), name="recommendations"),
    path("", PublicJobListView.as_view(), name="list"),
    path("<int:pk>/", PublicJobDetailView.as_view(), name="detail"),
    path("<int:job_id>/bookmark/", SeekerBookmarkView.as_view(), name="bookmark"),
    path("manage/", JobCreateView.as_view(), name="manage-list"),
    path("manage/<int:pk>/", JobDetailView.as_view(), name="manage-detail"),
]
