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
from talentwright.recruiter_copilot.orchestrator.engine import CopilotOrchestrator
from talentwright.resume_analysis.exceptions import LLMConfigurationError

logger = logging.getLogger(__name__)


class JobSessionListCreateView(APIView):
    """List or create chat sessions for a specific job posting."""

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id: int) -> Response:
        # 1. Explicit job lookup
        job = Job.objects.filter(id=job_id).first()
        if not job:
            return Response(
                {"error": "Job posting not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Explicit employer check with staff/superuser support
        employer = getattr(request.user, "employer_profile", None)
        if not employer and (request.user.is_staff or request.user.is_superuser):
            employer = job.employer

        if not employer:
            return Response(
                {"error": "Only verified employers can access copilot sessions."},
                status=status.HTTP_403_FORBIDDEN,
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
        # 1. Explicit job lookup
        job = Job.objects.filter(id=job_id).first()
        if not job:
            return Response(
                {"error": "Job posting not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Explicit employer check with staff/superuser support
        employer = getattr(request.user, "employer_profile", None)
        if not employer and (request.user.is_staff or request.user.is_superuser):
            employer = job.employer

        if not employer:
            return Response(
                {"error": "Only verified employers can create copilot sessions."},
                status=status.HTTP_403_FORBIDDEN,
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
        # 1. Explicit session lookup
        session = CopilotSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Copilot session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Explicit employer check with staff/superuser support
        employer = getattr(request.user, "employer_profile", None)
        if not employer and (request.user.is_staff or request.user.is_superuser):
            employer = session.employer

        if not employer:
            return Response(
                {"error": "Only employers can view copilot messages."},
                status=status.HTTP_403_FORBIDDEN,
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
        # 1. Explicit session lookup
        session = CopilotSession.objects.filter(id=session_id).first()
        if not session:
            return Response(
                {"error": "Copilot session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Explicit employer check with staff/superuser support
        employer = getattr(request.user, "employer_profile", None)
        if not employer and (request.user.is_staff or request.user.is_superuser):
            employer = session.employer

        if not employer:
            return Response(
                {"error": "Only employers can send copilot messages."},
                status=status.HTTP_403_FORBIDDEN,
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

        # 6. Call Copilot Orchestrator to generate intelligent reply with tool support
        try:
            orchestrator = CopilotOrchestrator()
            assistant_text, metadata = orchestrator.run(
                session=session,
                new_user_message=user_text,
                exclude_message_id=user_message.id,
            )
        except LLMConfigurationError as e:
            logger.exception("LLM configuration error in copilot: %s", e)
            assistant_text = (
                "⚠️ **AI Service Configuration Notice**\n\n"
                "The AI service has not been configured with an API key on this server. "
                "Please configure `SCREENING_LLM_API_KEY` (or `OPENROUTER_API_KEY` / `OPENAI_API_KEY`) in the environment variables to enable the AI recruiter."
            )
            metadata = {"error": str(e), "error_type": "configuration"}
        except Exception as e:
            logger.exception("Unexpected error in recruiter copilot: %s", e)
            assistant_text = (
                "⚠️ **AI Service Notice**\n\n"
                f"An error occurred while communicating with the AI model: `{str(e)}`. "
                "Please verify that your AI API key is valid and has sufficient quota/credits."
            )
            metadata = {"error": str(e), "error_type": "runtime"}

        # 7. Save assistant reply in database
        assistant_message = CopilotMessage.objects.create(
            session=session,
            role=MessageRole.ASSISTANT,
            content=assistant_text,
            metadata=metadata,
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
