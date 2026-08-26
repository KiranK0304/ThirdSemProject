from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from talentwright.applications.models import Application
from talentwright.applications.models import ApplicationStatus
from talentwright.jobs.api.serializers import PublicJobSerializer
from talentwright.users.api.auth_serializers import ResumeSerializer
from talentwright.users.models import Resume, SeekerProfile


class ApplicationSeekerSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = SeekerProfile
        fields = [
            "id",
            "user_email",
            "user_name",
            "phone",
            "bio",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApplicationSerializer(serializers.ModelSerializer):
    job = PublicJobSerializer(read_only=True)
    seeker = ApplicationSeekerSerializer(read_only=True)
    resume = ResumeSerializer(read_only=True)
    resume_id = serializers.PrimaryKeyRelatedField(
        queryset=Resume.objects.all(),
        source="resume",
        write_only=True,
        required=False,
        allow_null=True,
    )
    cover_letter = serializers.CharField(allow_blank=True, required=False)

    class Meta:
        model = Application
        fields = [
            "id",
            "job",
            "seeker",
            "resume",
            "resume_id",
            "cover_letter",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "job",
            "seeker",
            "resume",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        job = self.context.get("job")
        seeker = self.context.get("seeker")

        if job and seeker and Application.objects.filter(job=job, seeker=seeker).exists():
            raise serializers.ValidationError({"non_field_errors": ["You have already applied to this job."]})

        resume = attrs.get("resume")
        if resume and seeker and resume.seeker != seeker:
            raise serializers.ValidationError({"resume_id": ["The selected resume does not belong to you."]})

        application = Application(
            job=job,
            seeker=seeker,
            resume=resume,
            cover_letter=attrs.get("cover_letter", ""),
        )

        try:
            application.full_clean(exclude=["id", "status", "created_at", "updated_at"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            return Application.objects.create(
                job=self.context["job"],
                seeker=self.context["seeker"],
                resume=validated_data.get("resume"),
                cover_letter=validated_data.get("cover_letter", ""),
            )


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_status(self, value):
        allowed_statuses = [
            ApplicationStatus.SUBMITTED,
            ApplicationStatus.UNDER_REVIEW,
            ApplicationStatus.SHORTLISTED,
            ApplicationStatus.REJECTED,
        ]
        if value not in allowed_statuses:
            raise serializers.ValidationError(
                f"Invalid status for employer update. Choose one of: {', '.join(allowed_statuses)}."
            )
        return value

