from rest_framework import serializers

from talentwright.applications.models import Application, ApplicationStatus
from talentwright.jobs.models import JobStatus


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["id", "job", "seeker", "cover_letter", "status", "created_at", "updated_at"]
        read_only_fields = ["id", "job", "seeker", "status", "created_at", "updated_at"]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ["id", "cover_letter", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        job = self.context["job"]
        if job.status != JobStatus.OPEN:
            raise serializers.ValidationError("Applications can only be submitted to open jobs.")
        seeker = self.context["request"].user.seeker_profile
        if Application.objects.filter(job=job, seeker=seeker).exists():
            raise serializers.ValidationError("You have already applied to this job.")
        return attrs

    def create(self, validated_data):
        return Application.objects.create(
            job=self.context["job"],
            seeker=self.context["request"].user.seeker_profile,
            **validated_data,
        )


class ApplicationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ApplicationStatus.choices)
