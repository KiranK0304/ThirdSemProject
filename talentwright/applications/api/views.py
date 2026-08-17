from django.shortcuts import get_object_or_404
from rest_framework import generics

from talentwright.applications.api.serializers import ApplicationSerializer
from talentwright.applications.api.serializers import ApplicationStatusUpdateSerializer
from talentwright.applications.models import Application
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.users.api.permissions import IsSeeker
from talentwright.users.api.permissions import IsVerifiedEmployer
from talentwright.users.models import VerificationStatus


class JobApplicationCreateView(generics.CreateAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsSeeker]

    def get_job(self):
        return get_object_or_404(
            Job.objects.select_related("employer", "employer__user"),
            pk=self.kwargs["job_id"],
            status=JobStatus.OPEN,
            employer__verification_status=VerificationStatus.APPROVED,
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["job"] = self.get_job()
        context["seeker"] = self.request.user.seeker_profile
        return context

    def perform_create(self, serializer):
        serializer.save()


class JobApplicationsListView(generics.ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsVerifiedEmployer]

    def get_job(self):
        return get_object_or_404(
            Job.objects.select_related("employer", "employer__user"),
            pk=self.kwargs["job_id"],
            employer=self.request.user.employer_profile,
        )

    def get_queryset(self):
        job = self.get_job()
        return (
            Application.objects.select_related(
                "job",
                "job__employer",
                "job__employer__user",
                "seeker",
                "seeker__user",
            )
            .filter(job=job)
            .order_by("-created_at")
        )


class EmployerApplicationsListView(generics.ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsVerifiedEmployer]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        return (
            Application.objects.select_related(
                "job",
                "job__employer",
                "job__employer__user",
                "seeker",
                "seeker__user",
            )
            .filter(job__employer=employer)
            .order_by("-created_at")
        )


class EmployerApplicationStatusUpdateView(generics.UpdateAPIView):
    serializer_class = ApplicationStatusUpdateSerializer
    permission_classes = [IsVerifiedEmployer]
    http_method_names = ["patch", "options", "head"]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        return Application.objects.filter(job__employer=employer)


class SeekerApplicationsListView(generics.ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        seeker = self.request.user.seeker_profile
        return (
            Application.objects.select_related(
                "job",
                "job__employer",
                "job__employer__user",
                "seeker",
                "seeker__user",
            )
            .filter(seeker=seeker)
            .order_by("-created_at")
        )


class SeekerApplicationDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        seeker = self.request.user.seeker_profile
        return Application.objects.select_related(
            "job",
            "job__employer",
            "job__employer__user",
            "seeker",
            "seeker__user",
        ).filter(seeker=seeker)


