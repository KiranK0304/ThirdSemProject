from django.urls import path

from talentwright.message.api.views import ConversationMarkAsReadView
from talentwright.message.api.views import ConversationMessagesListCreateView
from talentwright.message.api.views import EmployerApprovedConversationsListView
from talentwright.message.api.views import EmployerChatRequestsListView
from talentwright.message.api.views import EmployerChatRequestStatusUpdateView
from talentwright.message.api.views import SeekerApprovedConversationsListView
from talentwright.message.api.views import SeekerChatRequestCreateView
from talentwright.message.api.views import SeekerChatRequestDetailView
from talentwright.message.api.views import SeekerPendingRequestsListView

app_name = "message"

urlpatterns = [
    # Seeker request endpoints
    path(
        "requests/",
        SeekerChatRequestCreateView.as_view(),
        name="seeker-request-create",
    ),
    path(
        "pending/",
        SeekerPendingRequestsListView.as_view(),
        name="seeker-pending-requests",
    ),
    path(
        "approved/",
        SeekerApprovedConversationsListView.as_view(),
        name="seeker-approved-conversations",
    ),
    path(
        "conversations/",
        SeekerApprovedConversationsListView.as_view(),
        name="seeker-conversations",
    ),
    path(
        "requests/<int:pk>/",
        SeekerChatRequestDetailView.as_view(),
        name="seeker-request-detail",
    ),
    # Employer endpoints
    path(
        "employer/requests/",
        EmployerChatRequestsListView.as_view(),
        name="employer-requests-list",
    ),
    path(
        "employer/requests/<int:pk>/status/",
        EmployerChatRequestStatusUpdateView.as_view(),
        name="employer-request-status-update",
    ),
    path(
        "employer/conversations/",
        EmployerApprovedConversationsListView.as_view(),
        name="employer-approved-conversations",
    ),
    # Conversation messaging endpoints
    path(
        "conversations/<int:chat_request_id>/messages/",
        ConversationMessagesListCreateView.as_view(),
        name="conversation-messages",
    ),
    path(
        "conversations/<int:chat_request_id>/read/",
        ConversationMarkAsReadView.as_view(),
        name="conversation-mark-read",
    ),
]
