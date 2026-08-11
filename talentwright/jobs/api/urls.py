from django.urls import path

from talentwright.jobs.api.views import JobCreateView

app_name = "jobs"

urlpatterns = [
    path("", JobCreateView.as_view(), name="create"),
]
