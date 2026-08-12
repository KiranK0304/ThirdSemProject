from django.urls import path

from talentwright.jobs.api.views import JobCreateView
from talentwright.jobs.api.views import JobDetailView
from talentwright.jobs.api.views import PublicJobDetailView
from talentwright.jobs.api.views import PublicJobListView

app_name = "jobs"

urlpatterns = [
    path("", PublicJobListView.as_view(), name="list"),
    path("<int:pk>/", PublicJobDetailView.as_view(), name="detail"),
    path("manage/", JobCreateView.as_view(), name="manage-list"),
    path("manage/<int:pk>/", JobDetailView.as_view(), name="manage-detail"),
]
