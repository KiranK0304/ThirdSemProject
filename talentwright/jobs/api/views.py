from rest_framework.generics import ListCreateAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView

from talentwright.jobs.api.serializers import JobCreateSerializer
from talentwright.jobs.models import Job
from talentwright.users.api.permissions import IsVerifiedEmployer


class EmployerJobQuerysetMixin:
    queryset = Job.objects.select_related("employer", "employer__user")
    permission_classes = [IsVerifiedEmployer]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        return self.queryset.filter(employer=employer)


class JobCreateView(EmployerJobQuerysetMixin, ListCreateAPIView):
    serializer_class = JobCreateSerializer


class JobDetailView(EmployerJobQuerysetMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = JobCreateSerializer
