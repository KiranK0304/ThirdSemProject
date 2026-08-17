from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.generics import ListCreateAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny

from talentwright.jobs.api.serializers import JobCreateSerializer
from talentwright.jobs.api.serializers import PublicJobSerializer
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
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


class JobCreateView(EmployerJobQuerysetMixin, ListCreateAPIView):
    serializer_class = JobCreateSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "description", "location"]
    ordering_fields = ["created_at", "salary_min", "salary_max", "title", "status"]
    ordering = ["-created_at"]


class JobDetailView(EmployerJobQuerysetMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = JobCreateSerializer

