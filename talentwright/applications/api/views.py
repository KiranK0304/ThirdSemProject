from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from talentwright.applications.api.serializers import (
    ApplicationSerializer,
    ApplicationStatusUpdateSerializer,
    InterviewSerializer,
    JobApplicantSerializer,
    JobOfferDecisionSerializer,
    JobOfferSerializer,
)
from talentwright.applications.models import (
    Application,
    ApplicationStatus,
    Interview,
    JobOffer,
    JobOfferStatus,
)
from talentwright.jobs.models import Job, JobStatus
from talentwright.notifications.models import Notification, NotificationType
from talentwright.notifications.services import (
    notify_application_status_changed,
    notify_application_submitted,
    send_application_rejection_email,
    send_application_shortlist_email,
)
from talentwright.users.api.permissions import IsSeeker, IsVerifiedEmployer
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
                "resume_analysis",
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
                "resume_analysis",
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
            if instance.status == ApplicationStatus.SHORTLISTED:
                send_application_shortlist_email(instance)
            elif instance.status == ApplicationStatus.REJECTED:
                send_application_rejection_email(instance, instance.rejection_note)


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


class EmployerJobOfferCreateUpdateView(APIView):
    """
    Allows employer to create, update, or retrieve an official job offer for an applicant.
    """

    permission_classes = [IsVerifiedEmployer]

    def get_application(self, application_id):
        return get_object_or_404(
            Application.objects.select_related("job", "job__employer", "job__employer__user", "seeker", "seeker__user"),
            pk=application_id,
            job__employer=self.request.user.employer_profile,
        )

    def get(self, request, application_id):
        application = self.get_application(application_id)
        if not hasattr(application, "offer"):
            return Response({"detail": "No offer extended yet."}, status=status.HTTP_404_NOT_FOUND)
        serializer = JobOfferSerializer(application.offer)
        return Response(serializer.data)

    def post(self, request, application_id):
        application = self.get_application(application_id)
        offer = getattr(application, "offer", None)
        serializer = JobOfferSerializer(instance=offer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        saved_offer = serializer.save(application=application)

        # Automatically update application status to OFFERED
        if application.status != ApplicationStatus.OFFERED:
            application.status = ApplicationStatus.OFFERED
            application.save()

        # Send notification to applicant
        Notification.objects.create(
            recipient=application.seeker.user,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGED,
            title="Official Job Offer Received! 🎉",
            message=f"{application.job.employer.company_name} has extended an official employment offer for {application.job.title}.",
            related_url="/applications",
        )

        return Response(
            JobOfferSerializer(saved_offer).data,
            status=status.HTTP_200_OK if offer else status.HTTP_201_CREATED,
        )


class SeekerJobOfferDecisionView(APIView):
    """
    Allows a candidate to accept or decline a formal employment offer.
    """

    permission_classes = [IsSeeker]

    def post(self, request, application_id):
        application = get_object_or_404(
            Application.objects.select_related("job", "job__employer", "job__employer__user", "seeker", "seeker__user"),
            pk=application_id,
            seeker=request.user.seeker_profile,
        )
        if not hasattr(application, "offer"):
            return Response({"detail": "No offer found for this application."}, status=status.HTTP_404_NOT_FOUND)

        serializer = JobOfferDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]
        decline_reason = serializer.validated_data.get("decline_reason", "")

        offer = application.offer
        offer.status = decision
        offer.responded_at = timezone.now()
        if decline_reason:
            offer.decline_reason = decline_reason
        offer.save()

        # Notify employer
        action_verb = "accepted" if decision == "ACCEPTED" else "declined"
        Notification.objects.create(
            recipient=application.job.employer.user,
            notification_type=NotificationType.APPLICATION_STATUS_CHANGED,
            title=f"Offer {decision.capitalize()} by Candidate",
            message=f"{application.seeker.user.name} has {action_verb} your employment offer for {application.job.title}.",
            related_url=f"/employer/jobs/{application.job.id}/applicants",
        )

        return Response(JobOfferSerializer(offer).data)
