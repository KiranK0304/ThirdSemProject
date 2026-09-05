"""Serializers for Recruiter Copilot sessions and messages."""

from __future__ import annotations

from rest_framework import serializers

from talentwright.recruiter_copilot.models import CopilotMessage
from talentwright.recruiter_copilot.models import CopilotSession


class CopilotMessageSerializer(serializers.ModelSerializer):
    """Serializer for a single chat message."""

    class Meta:
        model = CopilotMessage
        fields = [
            "id",
            "role",
            "content",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "role", "created_at"]


class CopilotSessionSerializer(serializers.ModelSerializer):
    """Serializer for a copilot chat session summary."""

    message_count = serializers.SerializerMethodField()

    class Meta:
        model = CopilotSession
        fields = [
            "id",
            "job_id",
            "title",
            "message_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "job_id", "created_at", "updated_at"]

    def get_message_count(self, obj: CopilotSession) -> int:
        return obj.messages.count()
