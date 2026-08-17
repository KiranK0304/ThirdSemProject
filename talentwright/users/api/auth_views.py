from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .auth_serializers import (
    CustomTokenObtainPairSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserMeSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    API view for registering a new user and returning immediate JWT access & refresh tokens.
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens for the newly registered user
        refresh = RefreshToken.for_user(user)

        user_data = UserMeSerializer(user).data
        response_data = {
            "user": user_data,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    API view for authenticating user credentials and issuing JWT access & refresh tokens.
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]


class CustomTokenRefreshView(TokenRefreshView):
    """
    API view for refreshing expired access tokens using a valid refresh token.
    """
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    API view for logging out a user by blacklisting their refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh_token = serializer.validated_data["refresh"]
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(
                {"detail": "Successfully logged out. Refresh token blacklisted."},
                status=status.HTTP_200_OK,
            )
        except TokenError as e:
            return Response(
                {"detail": f"Invalid or expired refresh token: {e!s}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


from talentwright.users.api.permissions import IsAdmin
from talentwright.users.models import EmployerProfile, VerificationStatus
from .auth_serializers import (
    CustomTokenObtainPairSerializer,
    EmployerProfileAdminSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserMeSerializer,
)


class UserMeView(generics.RetrieveUpdateAPIView):
    """
    API View for retrieving and updating the current authenticated user's profile information.
    """
    serializer_class = UserMeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class AdminEmployerListView(generics.ListAPIView):
    """
    API View for admins to list all employer profiles (with optional ?status=PENDING filter).
    """
    serializer_class = EmployerProfileAdminSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = EmployerProfile.objects.select_related("user").all().order_by("-created_at")
        status_param = self.request.query_params.get("status")
        if status_param:
            normalized_status = status_param.upper()
            if normalized_status not in VerificationStatus.values:
                allowed_statuses = ", ".join(VerificationStatus.values)
                raise ValidationError({"status": f"Invalid status. Allowed values: {allowed_statuses}."})
            queryset = queryset.filter(verification_status=normalized_status)
        return queryset


class AdminEmployerApproveView(APIView):
    """
    API View for admins to approve an employer profile.
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            profile = EmployerProfile.objects.get(pk=pk)
        except EmployerProfile.DoesNotExist:
            return Response({"detail": "Employer profile not found."}, status=status.HTTP_404_NOT_FOUND)

        profile.verification_status = VerificationStatus.APPROVED
        profile.save()
        serializer = EmployerProfileAdminSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminEmployerRejectView(APIView):
    """
    API View for admins to reject an employer profile.
    """
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            profile = EmployerProfile.objects.get(pk=pk)
        except EmployerProfile.DoesNotExist:
            return Response({"detail": "Employer profile not found."}, status=status.HTTP_404_NOT_FOUND)

        profile.verification_status = VerificationStatus.REJECTED
        profile.save()
        serializer = EmployerProfileAdminSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from talentwright.users.api.permissions import IsSeeker
from talentwright.users.models import Resume
from .auth_serializers import ResumeSerializer


class SeekerResumeListCreateView(generics.ListCreateAPIView):
    """
    API view for seekers to list their resumes and upload new resumes (up to 3 max).
    """
    serializer_class = ResumeSerializer
    permission_classes = [IsSeeker]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Resume.objects.filter(seeker=self.request.user.seeker_profile).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(seeker=self.request.user.seeker_profile)


class SeekerResumeDetailView(generics.RetrieveDestroyAPIView):
    """
    API view for seekers to retrieve or delete an individual resume.
    """
    serializer_class = ResumeSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return Resume.objects.filter(seeker=self.request.user.seeker_profile)


