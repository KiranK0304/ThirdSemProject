from rest_framework import serializers

from talentwright.complaints.models import Complaint, ComplaintStatus


class ComplaintSerializer(serializers.ModelSerializer):
    reporter_email = serializers.EmailField(source="reporter.email", read_only=True)
    reporter_name = serializers.CharField(source="reporter.name", read_only=True)

    class Meta:
        model = Complaint
        fields = ["id", "reporter", "reporter_email", "reporter_name", "category", "subject", "description", "status", "admin_notes", "created_at", "updated_at"]
        read_only_fields = ["id", "reporter", "reporter_email", "reporter_name", "status", "admin_notes", "created_at", "updated_at"]

    def validate_category(self, value):
        if value not in {"ACCOUNT", "JOB", "APPLICATION", "MESSAGE", "OTHER"}:
            raise serializers.ValidationError("Choose a valid complaint category.")
        return value


class ComplaintStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ["status", "admin_notes"]

    def validate_status(self, value):
        if value not in ComplaintStatus.values:
            raise serializers.ValidationError("Choose a valid complaint status.")
        return value
