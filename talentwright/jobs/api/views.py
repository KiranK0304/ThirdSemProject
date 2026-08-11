from rest_framework.generics import CreateAPIView

from talentwright.jobs.api.serializers import JobCreateSerializer
from talentwright.jobs.models import Job
from talentwright.users.api.permissions import IsVerifiedEmployer


class JobCreateView(CreateAPIView):
    queryset = Job.objects.select_related("employer", "employer__user")
    serializer_class = JobCreateSerializer
    permission_classes = [IsVerifiedEmployer]
