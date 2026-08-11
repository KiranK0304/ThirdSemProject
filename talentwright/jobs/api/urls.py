from django.urls import path

from talentwright.jobs.api.views import JobCreateView
from talentwright.jobs.api.views import JobDetailView

app_name = "jobs"

urlpatterns = [
    path("", JobCreateView.as_view(), name="create"),
    path("<int:pk>/", JobDetailView.as_view(), name="detail"),
]
