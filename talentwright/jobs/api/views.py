from django.shortcuts import get_object_or_404
from django.db.models import Case
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from rest_framework import filters
from rest_framework import generics
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.generics import ListCreateAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from talentwright.jobs.api.serializers import JobAlertSerializer
from talentwright.jobs.api.serializers import JobBookmarkSerializer
from talentwright.jobs.api.serializers import JobCreateSerializer
from talentwright.jobs.api.serializers import PublicJobSerializer
from talentwright.jobs.api.serializers import RecommendedJobSerializer
from talentwright.jobs.api.serializers import SavedJobSerializer
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobAlert
from talentwright.jobs.models import JobBookmark
from talentwright.jobs.models import JobStatus
from talentwright.jobs.models import SavedJob
from talentwright.jobs.services import matching_jobs_for_alert
from talentwright.users.api.permissions import IsSeeker
from talentwright.users.api.permissions import IsVerifiedEmployer
from talentwright.users.models import VerificationStatus


class EmployerJobQuerysetMixin:
    queryset = Job.objects.select_related("employer", "employer__user")
    permission_classes = [IsVerifiedEmployer]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        qs = self.queryset.filter(employer=employer)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs


class PublicOpenJobQuerysetMixin:
    queryset = Job.objects.select_related("employer", "employer__user")
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = self.queryset.filter(
            status=JobStatus.OPEN,
            employer__verification_status=VerificationStatus.APPROVED,
        )
        employment_type = self.request.query_params.get("employment_type")
        if employment_type:
            qs = qs.filter(employment_type=employment_type)
        location = self.request.query_params.get("location")
        if location:
            qs = qs.filter(location__icontains=location)
        min_salary = self.request.query_params.get("min_salary")
        if min_salary:
            qs = qs.filter(salary_max__gte=min_salary)
        return qs


class PublicJobListView(PublicOpenJobQuerysetMixin, ListAPIView):
    serializer_class = PublicJobSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "location", "employer__company_name"]
    ordering_fields = ["created_at", "salary_min", "salary_max", "title"]
    ordering = ["-created_at"]


class PublicJobDetailView(PublicOpenJobQuerysetMixin, RetrieveAPIView):
    serializer_class = PublicJobSerializer


class SeekerRecommendedJobListView(ListAPIView):
    serializer_class = RecommendedJobSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        seeker = self.request.user.seeker_profile
        base_queryset = Job.objects.select_related("employer", "employer__user").filter(
            status=JobStatus.OPEN,
            employer__verification_status=VerificationStatus.APPROVED,
        ).exclude(applications__seeker=seeker)

        employment_types = list(
            seeker.applications.values_list("job__employment_type", flat=True).distinct()
        )
        locations = list(
            seeker.applications.exclude(job__location="")
            .values_list("job__location", flat=True)
            .distinct()
        )
        bookmarked_employment_types = list(
            seeker.job_bookmarks.values_list("job__employment_type", flat=True).distinct()
        )
        bookmarked_locations = list(
            seeker.job_bookmarks.exclude(job__location="")
            .values_list("job__location", flat=True)
            .distinct()
        )
        employment_types = list(set(employment_types + bookmarked_employment_types))
        locations = list(set(locations + bookmarked_locations))

        score = Case(
            When(employment_type__in=employment_types, then=Value(3)),
            default=Value(0),
            output_field=IntegerField(),
        )
        if locations:
            location_match = Q()
            for location in locations:
                location_match |= Q(location__icontains=location)
            score = score + Case(
                When(location_match, then=Value(2)),
                default=Value(0),
                output_field=IntegerField(),
            )

        return base_queryset.annotate(match_score=score).order_by("-match_score", "-created_at")


class JobCreateView(EmployerJobQuerysetMixin, ListCreateAPIView):
    serializer_class = JobCreateSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "location"]
    ordering_fields = ["created_at", "salary_min", "salary_max", "title", "status"]
    ordering = ["-created_at"]


class JobDetailView(EmployerJobQuerysetMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = JobCreateSerializer


class SeekerBookmarkListView(ListAPIView):
    serializer_class = JobBookmarkSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return JobBookmark.objects.select_related(
            "job",
            "job__employer",
            "job__employer__user",
        ).filter(seeker=self.request.user.seeker_profile)


class SeekerBookmarkView(APIView):
    permission_classes = [IsSeeker]

    def post(self, request, job_id):
        job = get_object_or_404(
            Job.objects.select_related("employer", "employer__user"),
            pk=job_id,
            status=JobStatus.OPEN,
            employer__verification_status=VerificationStatus.APPROVED,
        )
        bookmark, created = JobBookmark.objects.get_or_create(
            seeker=request.user.seeker_profile,
            job=job,
        )
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        response_data = JobBookmarkSerializer(
            bookmark,
            context={"request": request},
        ).data
        return Response(response_data, status=response_status)

    def delete(self, request, job_id):
        deleted, _ = JobBookmark.objects.filter(
            seeker=request.user.seeker_profile,
            job_id=job_id,
        ).delete()
        if not deleted:
            return Response(
                {"detail": "Bookmark not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SavedJobListView(generics.ListAPIView):
    serializer_class = SavedJobSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return SavedJob.objects.select_related(
            "job",
            "job__employer",
            "job__employer__user",
        ).filter(seeker=self.request.user.seeker_profile)


class SavedJobCreateDeleteView(APIView):
    permission_classes = [IsSeeker]

    def _get_public_job(self):
        return get_object_or_404(
            Job.objects.select_related("employer", "employer__user"),
            pk=self.kwargs["job_id"],
            status=JobStatus.OPEN,
            employer__verification_status=VerificationStatus.APPROVED,
        )

    def post(self, request, job_id):
        job = self._get_public_job()
        saved_job, created = SavedJob.objects.get_or_create(
            seeker=request.user.seeker_profile,
            job=job,
        )
        serializer = SavedJobSerializer(saved_job, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def delete(self, request, job_id):
        saved_job = get_object_or_404(
            SavedJob,
            seeker=request.user.seeker_profile,
            job_id=job_id,
        )
        saved_job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JobAlertListCreateView(generics.ListCreateAPIView):
    serializer_class = JobAlertSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return JobAlert.objects.filter(seeker=self.request.user.seeker_profile)

    def perform_create(self, serializer):
        serializer.save(seeker=self.request.user.seeker_profile)


class JobAlertDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = JobAlertSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return JobAlert.objects.filter(seeker=self.request.user.seeker_profile)


class JobAlertMatchesListView(generics.ListAPIView):
    serializer_class = PublicJobSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        alert = get_object_or_404(
            JobAlert,
            pk=self.kwargs["pk"],
            seeker=self.request.user.seeker_profile,
        )
        return matching_jobs_for_alert(alert)

