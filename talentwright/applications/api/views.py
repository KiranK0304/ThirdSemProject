from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from talentwright.applications.api.serializers import (
    ApplicationCreateSerializer,
    ApplicationSerializer,
    ApplicationStatusSerializer,
)
from talentwright.applications.models import Application, ApplicationStatus
from talentwright.jobs.models import Job
from talentwright.notifications.services import (
    notify_application_status_changed,
    notify_application_submitted,
)
from talentwright.users.api.permissions import IsEmployer, IsSeeker


class JobApplicationCreateView(CreateAPIView):
    serializer_class = ApplicationCreateSerializer
    permission_classes = [IsSeeker]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["job"] = get_object_or_404(Job, pk=self.kwargs["job_id"])
        return context

    def perform_create(self, serializer):
        application = serializer.save()
        notify_application_submitted(application)


class SeekerApplicationListView(ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return Application.objects.filter(seeker=self.request.user.seeker_profile).select_related("job", "seeker__user")


class SeekerApplicationDetailView(RetrieveDestroyAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return Application.objects.filter(seeker=self.request.user.seeker_profile).select_related("job", "seeker__user")

    def perform_destroy(self, instance):
        instance.status = ApplicationStatus.WITHDRAWN
        instance.save(update_fields=["status", "updated_at"])


class EmployerApplicationListView(ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsEmployer]

    def get_queryset(self):
        return Application.objects.filter(job__employer=self.request.user.employer_profile).select_related("job", "seeker__user")


class JobApplicantListView(ListAPIView):
    serializer_class = ApplicationSerializer
    permission_classes = [IsEmployer]

    def get_queryset(self):
        return Application.objects.filter(
            job_id=self.kwargs["job_id"],
            job__employer=self.request.user.employer_profile,
        ).select_related("job", "seeker__user")


class EmployerApplicationStatusView(APIView):
    permission_classes = [IsEmployer]

    def patch(self, request, pk):
        application = get_object_or_404(
            Application.objects.select_related("job", "seeker__user"),
            pk=pk,
            job__employer=request.user.employer_profile,
        )
        serializer = ApplicationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]
        if application.status != new_status:
            application.status = new_status
            application.save(update_fields=["status", "updated_at"])
            notify_application_status_changed(application)
        return Response(ApplicationSerializer(application).data, status=status.HTTP_200_OK)
