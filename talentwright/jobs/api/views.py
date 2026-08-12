from rest_framework.generics import ListAPIView
from rest_framework.generics import ListCreateAPIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny

from talentwright.jobs.api.serializers import JobCreateSerializer
from talentwright.jobs.api.serializers import PublicJobSerializer
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.users.models import VerificationStatus
from talentwright.users.api.permissions import IsVerifiedEmployer


class EmployerJobQuerysetMixin:
    queryset = Job.objects.select_related("employer", "employer__user")
    permission_classes = [IsVerifiedEmployer]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        return self.queryset.filter(employer=employer)


class PublicOpenJobQuerysetMixin:
    queryset = Job.objects.select_related("employer", "employer__user")
    permission_classes = [AllowAny]

    def get_queryset(self):
        return self.queryset.filter(
            status=JobStatus.OPEN,
            employer__verification_status=VerificationStatus.APPROVED,
        )


class PublicJobListView(PublicOpenJobQuerysetMixin, ListAPIView):
    serializer_class = PublicJobSerializer


class PublicJobDetailView(PublicOpenJobQuerysetMixin, RetrieveAPIView):
    serializer_class = PublicJobSerializer


class JobCreateView(EmployerJobQuerysetMixin, ListCreateAPIView):
    serializer_class = JobCreateSerializer


class JobDetailView(EmployerJobQuerysetMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = JobCreateSerializer
