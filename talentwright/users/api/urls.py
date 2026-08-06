from django.urls import path

from .auth_views import (
    AdminEmployerApproveView,
    AdminEmployerListView,
    AdminEmployerRejectView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    LogoutView,
    RegisterView,
    UserMeView,
)

app_name = "auth"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="login"),
    path("refresh/", CustomTokenRefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", UserMeView.as_view(), name="me"),
    path("admin/employers/", AdminEmployerListView.as_view(), name="admin-employer-list"),
    path("admin/employers/<int:pk>/approve/", AdminEmployerApproveView.as_view(), name="admin-employer-approve"),
    path("admin/employers/<int:pk>/reject/", AdminEmployerRejectView.as_view(), name="admin-employer-reject"),
]

