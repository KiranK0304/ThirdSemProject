from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from talentwright.jobs.models import Job
from talentwright.jobs.models import JobBookmark
from talentwright.users.models import EmployerProfile


class PublicEmployerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerProfile
        fields = [
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


class JobBookmarkSerializer(serializers.ModelSerializer):
    job = PublicJobSerializer(read_only=True)

    class Meta:
        model = JobBookmark
        fields = ["id", "job", "created_at"]
        read_only_fields = fields
