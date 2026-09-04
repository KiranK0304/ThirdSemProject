from rest_framework import serializers

from talentwright.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "related_url",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields
