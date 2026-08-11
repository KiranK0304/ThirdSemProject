from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from talentwright.jobs.models import Job


class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "description",
            "location",
            "employment_type",
            "salary_min",
            "salary_max",
            "salary_currency",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate(self, attrs):
        request = self.context.get("request")
        employer = request.user.employer_profile

        job = Job(employer=employer, **attrs)
        try:
            job.full_clean(exclude=["id", "status", "created_at", "updated_at"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)

        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        employer = request.user.employer_profile

        with transaction.atomic():
            return Job.objects.create(employer=employer, **validated_data)
