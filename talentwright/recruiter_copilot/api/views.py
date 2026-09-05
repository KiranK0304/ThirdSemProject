"""Explicit API views for Recruiter Copilot sessions and messages."""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from talentwright.jobs.models import Job
from talentwright.recruiter_copilot.api.serializers import CopilotMessageSerializer
from talentwright.recruiter_copilot.api.serializers import CopilotSessionSerializer
from talentwright.recruiter_copilot.models import CopilotMessage
from talentwright.recruiter_copilot.models import CopilotSession
from talentwright.recruiter_copilot.models import MessageRole

logger = logging.getLogger(__name__)


class JobSessionListCreateView(APIView):
    """List or create chat sessions for a specific job posting."""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int) -> Response:
        # 1. Explicit employer check
        employer = getattr(request.user, "employer_profile", None)
        if not employer:
            return Response(
                {"error": "Only verified employers can access copilot sessions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2. Explicit job lookup
        job = Job.objects.filter(id=job_id).first()
        if not job:
            return Response(
                {"error": "Job posting not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Explicit job ownership verification
        if job.employer_id != employer.id:
            return Response(
                {
                    "error": "You do not have permission to access sessions for this job."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # 4. Fetch and serialize sessions
        sessions = CopilotSession.objects.filter(
            job=job,
            employer=employer,
        ).order_by("-updated_at")

        serializer = CopilotSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, job_id: int) -> Response:
        # 1. Explicit employer check
        employer = getattr(request.user, "employer_profile", None)
        if not employer:
            return Response(
                {"error": "Only verified employers can create copilot sessions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2. Explicit job lookup
        job = Job.objects.filter(id=job_id).first()
        if not job:
            return Response(
                {"error": "Job posting not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Explicit ownership check
        if job.employer_id != employer.id:
            return Response(
                {"error": "You do not own this job posting."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 4. Read title parameter with explicit fallback
        title = request.data.get("title", "").strip()
        if not title:
            title = f"Chat for {job.title}"

        # 5. Explicit database creation
        session = CopilotSession.objects.create(
            job=job,
            employer=employer,
            title=title,
        )

        serializer = CopilotSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SessionMessageListCreateView(APIView):
    """Retrieve message history or send a message in a copilot session."""

    permission_classes = [IsAuthenticated]

    def get(self, request, session_id: int) -> Response:
        # 1. Explicit employer check
        employer = getattr(request.user, "employer_profile", None)
        if not employer:
            return Response(
                {"error": "Only employers can view copilot messages."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2. Explicit session lookup
        session = CopilotSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Copilot session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Explicit ownership verification
        if session.employer_id != employer.id:
            return Response(
                {"error": "You do not have access to this chat session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 4. Fetch messages ordered chronologically
        messages = session.messages.order_by("created_at")
        serializer = CopilotMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, session_id: int) -> Response:
        # 1. Explicit employer check
        employer = getattr(request.user, "employer_profile", None)
        if not employer:
            return Response(
                {"error": "Only employers can send copilot messages."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2. Explicit session lookup
        session = CopilotSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Copilot session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 3. Explicit ownership verification
        if session.employer_id != employer.id:
            return Response(
                {"error": "You do not have access to this chat session."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 4. Explicit message validation
        user_text = request.data.get("message", "").strip()
        if not user_text:
            return Response(
                {"error": "Message content cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 5. Explicitly save user message
        user_message = CopilotMessage.objects.create(
            session=session,
            role=MessageRole.USER,
            content=user_text,
        )

        # 6. Save assistant placeholder reply (advanced agent will connect here)
        assistant_message = CopilotMessage.objects.create(
            session=session,
            role=MessageRole.ASSISTANT,
            content="Copilot initialized and ready. Candidate reasoning will be executed here.",
            metadata={},
        )

        # Update session timestamp
        session.save(update_fields=["updated_at"])

        return Response(
            {
                "session_id": session.id,
                "user_message": CopilotMessageSerializer(user_message).data,
                "assistant_message": CopilotMessageSerializer(assistant_message).data,
            },
            status=status.HTTP_201_CREATED,
        )
