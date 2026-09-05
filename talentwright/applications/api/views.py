from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from talentwright.applications.api.serializers import (
    ApplicationSerializer,
    ApplicationStatusUpdateSerializer,
    InterviewSerializer,
    JobApplicantSerializer,
)
from talentwright.applications.models import Application
from talentwright.applications.models import ApplicationStatus
from talentwright.applications.models import Interview
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.notifications.services import (
    notify_application_status_changed,
    notify_application_submitted,
)
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
        application = serializer.save()
        notify_application_submitted(application)


class JobApplicationsListView(generics.ListAPIView):
    serializer_class = JobApplicantSerializer
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
                "seeker",
                "seeker__user",
                "resume",
            )
            .filter(job=job)
            .order_by("-created_at")
        )


class EmployerApplicationsListView(generics.ListAPIView):
    serializer_class = JobApplicantSerializer
    permission_classes = [IsVerifiedEmployer]

    def get_queryset(self):
        employer = self.request.user.employer_profile
        return (
            Application.objects.select_related(
                "job",
                "seeker",
                "seeker__user",
                "resume",
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

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        instance = serializer.save()
        if previous_status != instance.status:
            notify_application_status_changed(instance)


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
                "resume",
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
            "resume",
        ).filter(seeker=seeker)

class EmployerInterviewCreateView(generics.CreateAPIView):
    serializer_class = InterviewSerializer
    permission_classes = [IsVerifiedEmployer]

    def get_application(self):
        return get_object_or_404(
            Application.objects.select_related("job", "job__employer", "seeker", "seeker__user"),
            pk=self.kwargs["application_id"],
            job__employer=self.request.user.employer_profile,
            status=ApplicationStatus.SHORTLISTED,
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["application"] = self.get_application()
        return context

    def perform_create(self, serializer):
        application = self.get_application()
        if hasattr(application, "interview"):
            raise ValidationError({"detail": "This application already has an interview."})
        serializer.save()


class EmployerInterviewListView(generics.ListAPIView):
    serializer_class = InterviewSerializer
    permission_classes = [IsVerifiedEmployer]

    def get_queryset(self):
        return Interview.objects.select_related(
            "application",
            "application__job",
            "application__seeker__user",
        ).filter(application__job__employer=self.request.user.employer_profile)


class SeekerInterviewListView(generics.ListAPIView):
    serializer_class = InterviewSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return Interview.objects.select_related(
            "application",
            "application__job",
            "application__seeker__user",
        ).filter(application__seeker=self.request.user.seeker_profile)


class EmployerInterviewUpdateView(generics.UpdateAPIView):
    serializer_class = InterviewSerializer
    permission_classes = [IsVerifiedEmployer]
    http_method_names = ["patch", "options", "head"]

    def get_queryset(self):
        return Interview.objects.select_related(
            "application",
            "application__job",
            "application__seeker__user",
        ).filter(application__job__employer=self.request.user.employer_profile)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["application"] = self.get_object().application
        return context

