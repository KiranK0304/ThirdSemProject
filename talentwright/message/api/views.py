from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from talentwright.message.api.serializers import ChatRequestCreateSerializer
from talentwright.message.api.serializers import ChatRequestDetailSerializer
from talentwright.message.api.serializers import ChatRequestStatusUpdateSerializer
from talentwright.message.api.serializers import MessageCreateSerializer
from talentwright.message.api.serializers import MessageSerializer
from talentwright.message.models import ChatRequest
from talentwright.message.models import ChatRequestStatus
from talentwright.message.models import Message
from talentwright.users.api.permissions import IsSeeker
from talentwright.users.api.permissions import IsVerifiedEmployer


class SeekerChatRequestCreateView(generics.CreateAPIView):
    """Allows job seekers to send a chat/connection request to an employer."""

    serializer_class = ChatRequestCreateSerializer
    permission_classes = [IsSeeker]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["seeker"] = self.request.user.seeker_profile
        return context


class SeekerPendingRequestsListView(generics.ListAPIView):
    """List pending chat requests sent by seeker awaiting employer response."""

    serializer_class = ChatRequestDetailSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        seeker = self.request.user.seeker_profile
        return (
            ChatRequest.objects.select_related(
                "seeker",
                "seeker__user",
                "employer",
                "employer__user",
            )
            .prefetch_related("messages", "messages__sender")
            .filter(seeker=seeker, status=ChatRequestStatus.PENDING)
            .order_by("-created_at")
        )


class SeekerApprovedConversationsListView(generics.ListAPIView):
    """List approved chat requests / conversations for seeker where chat is active."""

    serializer_class = ChatRequestDetailSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        seeker = self.request.user.seeker_profile
        return (
            ChatRequest.objects.select_related(
                "seeker",
                "seeker__user",
                "employer",
                "employer__user",
            )
            .prefetch_related("messages", "messages__sender")
            .filter(seeker=seeker, status=ChatRequestStatus.APPROVED)
            .order_by("-updated_at")
        )


class SeekerChatRequestDetailView(generics.RetrieveDestroyAPIView):
    """Retrieve or cancel a chat request by the seeker."""

    serializer_class = ChatRequestDetailSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        seeker = self.request.user.seeker_profile
        return (
            ChatRequest.objects.select_related(
                "seeker",
                "seeker__user",
                "employer",
                "employer__user",
            )
            .prefetch_related("messages", "messages__sender")
            .filter(seeker=seeker)
        )


class EmployerChatRequestsListView(generics.ListAPIView):
    """List chat requests received by employer with optional ?status= filtering."""

    serializer_class = ChatRequestDetailSerializer
    permission_classes = [IsVerifiedEmployer]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        queryset = (
            ChatRequest.objects.select_related(
                "seeker",
                "seeker__user",
                "employer",
                "employer__user",
            )
            .prefetch_related("messages", "messages__sender")
            .filter(employer=employer)
            .order_by("-created_at")
        )
        status_param = self.request.query_params.get("status")
        if status_param and status_param.upper() in ChatRequestStatus.values:
            queryset = queryset.filter(status=status_param.upper())
        return queryset


class EmployerApprovedConversationsListView(generics.ListAPIView):
    """List approved chat requests / conversations for employer."""

    serializer_class = ChatRequestDetailSerializer
    permission_classes = [IsVerifiedEmployer]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        return (
            ChatRequest.objects.select_related(
                "seeker",
                "seeker__user",
                "employer",
                "employer__user",
            )
            .prefetch_related("messages", "messages__sender")
            .filter(employer=employer, status=ChatRequestStatus.APPROVED)
            .order_by("-updated_at")
        )


class EmployerChatRequestStatusUpdateView(generics.UpdateAPIView):
    """Allows employer to update status of chat request (APPROVED/REJECTED)."""

    serializer_class = ChatRequestStatusUpdateSerializer
    permission_classes = [IsVerifiedEmployer]
    http_method_names = ["patch", "options", "head"]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        return ChatRequest.objects.filter(employer=employer)


class ConversationMessagesListCreateView(generics.GenericAPIView):
    """List and create messages inside an approved chat request/conversation."""

    permission_classes = [permissions.IsAuthenticated]

    def get_chat_request(self) -> ChatRequest:
        chat_request_id = self.kwargs["chat_request_id"]
        user = self.request.user
        chat_request = get_object_or_404(
            ChatRequest.objects.select_related("seeker__user", "employer__user"),
            pk=chat_request_id,
        )
        if user.id not in (chat_request.seeker.user_id, chat_request.employer.user_id):
            self.permission_denied(
                self.request,
                message="You are not a participant in this conversation.",
            )
        return chat_request

    def get(self, request, *args, **kwargs):
        chat_request = self.get_chat_request()
        if chat_request.status != ChatRequestStatus.APPROVED:
            return Response(
                {"detail": "Messages can only be accessed in approved conversations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        messages = (
            Message.objects.select_related("sender")
            .filter(chat_request=chat_request)
            .order_by("created_at")
        )
        serializer = MessageSerializer(
            messages,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        chat_request = self.get_chat_request()
        if chat_request.status != ChatRequestStatus.APPROVED:
            return Response(
                {"detail": "Cannot send messages to unapproved conversations."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MessageCreateSerializer(
            data=request.data,
            context={"request": request, "chat_request": chat_request},
        )
        serializer.is_valid(raise_exception=True)
        message = serializer.save()

        # Update updated_at on the conversation
        chat_request.save(update_fields=["updated_at"])

        response_serializer = MessageSerializer(message, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ConversationMarkAsReadView(APIView):
    """Marks unread messages received from the other party as read."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, chat_request_id: int):
        chat_request = get_object_or_404(
            ChatRequest.objects.select_related("seeker__user", "employer__user"),
            pk=chat_request_id,
        )
        user = request.user
        if user.id not in (chat_request.seeker.user_id, chat_request.employer.user_id):
            return Response(
                {"detail": "You are not a participant in this conversation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        updated_count = (
            Message.objects.filter(
                chat_request=chat_request,
                is_read=False,
            )
            .exclude(sender=user)
            .update(is_read=True)
        )

        return Response(
            {"detail": f"{updated_count} messages marked as read."},
            status=status.HTTP_200_OK,
        )
