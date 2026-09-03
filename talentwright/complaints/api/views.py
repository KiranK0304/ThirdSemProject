from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from talentwright.users.api.permissions import IsAdmin
from talentwright.complaints.models import Complaint
from .serializers import ComplaintSerializer, ComplaintStatusSerializer


class ComplaintListCreateView(generics.ListCreateAPIView):
    serializer_class = ComplaintSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Complaint.objects.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reporter=self.request.user)


class AdminComplaintListView(generics.ListAPIView):
    serializer_class = ComplaintSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = Complaint.objects.select_related("reporter").all()
        status_filter = self.request.query_params.get("status")
        return queryset.filter(status=status_filter) if status_filter else queryset


class AdminComplaintStatusView(generics.UpdateAPIView):
    serializer_class = ComplaintStatusSerializer
    permission_classes = [IsAdmin]
    queryset = Complaint.objects.all()
    http_method_names = ["patch", "options", "head"]
