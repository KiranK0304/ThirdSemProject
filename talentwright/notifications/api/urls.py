from django.urls import path

from talentwright.notifications.api.views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="list"),
    path("unread-count/", NotificationUnreadCountView.as_view(), name="unread-count"),
    path("<int:pk>/read/", NotificationMarkReadView.as_view(), name="mark-read"),
    path("read-all/", NotificationMarkAllReadView.as_view(), name="mark-all-read"),
]
