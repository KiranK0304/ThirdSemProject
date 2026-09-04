from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from talentwright.jobs.models import ALERT_CRITERIA_ERROR
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobAlert
from talentwright.jobs.models import JobBookmark
from talentwright.jobs.models import SavedJob
from talentwright.users.models import EmployerProfile


class PublicEmployerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerProfile
        fields = [
            "id",
            "company_name",
            "website",
        ]
        read_only_fields = fields


class JobCreateSerializer(serializers.ModelSerializer):
    _job_fields = (
        "title",
        "description",
        "location",
        "employment_type",
        "salary_min",
        "salary_max",
        "salary_currency",
    )

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
        read_only_fields = ["id", "created_at", "updated_at"]

    def _build_job(self, attrs):
        employer = self.context["request"].user.employer_profile
        instance = self.instance

        job_kwargs = {}
        for field in self._job_fields:
            if field in attrs:
                job_kwargs[field] = attrs[field]
            elif instance is not None:
                job_kwargs[field] = getattr(instance, field)

        job = Job(employer=employer, **job_kwargs)
        if instance is not None:
            job.pk = instance.pk
        return job

    def _validate_job(self, attrs):
        job = self._build_job(attrs)
        try:
            job.full_clean(exclude=["id", "status", "created_at", "updated_at"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

    def validate(self, attrs):
        self._validate_job(attrs)
        return attrs

    def create(self, validated_data):
        employer = self.context["request"].user.employer_profile

        with transaction.atomic():
            return Job.objects.create(employer=employer, **validated_data)

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)

        self._validate_job(validated_data)

        with transaction.atomic():
            instance.save()
        return instance


class PublicJobSerializer(serializers.ModelSerializer):
    employer = PublicEmployerSerializer(read_only=True)

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
            "created_at",
            "updated_at",
            "employer",
        ]
        read_only_fields = fields


class RecommendedJobSerializer(PublicJobSerializer):
    match_score = serializers.IntegerField(read_only=True)

    class Meta(PublicJobSerializer.Meta):
        fields = [*PublicJobSerializer.Meta.fields, "match_score"]


class SavedJobSerializer(serializers.ModelSerializer):
    job = PublicJobSerializer(read_only=True)

    class Meta:
        model = SavedJob
        fields = ["id", "job", "created_at"]
        read_only_fields = fields


class JobBookmarkSerializer(serializers.ModelSerializer):
    job = PublicJobSerializer(read_only=True)

    class Meta:
        model = JobBookmark
        fields = ["id", "job", "created_at"]
        read_only_fields = fields


class JobAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAlert
        fields = [
            "id",
            "keyword",
            "location",
            "employment_type",
            "minimum_salary",
            "frequency",
            "is_active",
            "last_sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_sent_at", "created_at", "updated_at"]

    def validate(self, attrs):
        instance = self.instance
        keyword = attrs.get("keyword", instance.keyword if instance else "")
        location = attrs.get("location", instance.location if instance else "")
        employment_type = attrs.get(
            "employment_type",
            instance.employment_type if instance else "",
        )
        minimum_salary = attrs.get(
            "minimum_salary",
            instance.minimum_salary if instance else None,
        )

        has_criteria = any(
            [keyword.strip(), location.strip(), employment_type, minimum_salary is not None]
        )
        if not has_criteria:
            raise serializers.ValidationError(ALERT_CRITERIA_ERROR)
        return attrs

