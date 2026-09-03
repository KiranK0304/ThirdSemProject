from django.urls import path

from .views import AdminComplaintListView, AdminComplaintStatusView, ComplaintListCreateView

app_name = "complaints"

urlpatterns = [
    path("", ComplaintListCreateView.as_view(), name="list-create"),
    path("admin/", AdminComplaintListView.as_view(), name="admin-list"),
    path("admin/<int:pk>/", AdminComplaintStatusView.as_view(), name="admin-status"),
]
