from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from talentwright.notifications.services import notify_employer_approved, notify_employer_rejected
from talentwright.users.api.permissions import IsAdmin, IsSeeker
from talentwright.users.email_verification import send_verification_email, verify_token
from talentwright.users.models import EmployerProfile, Resume, VerificationStatus

from .auth_serializers import (
    CustomTokenObtainPairSerializer,
    EmployerProfileAdminSerializer,
    LogoutSerializer,
    PublicCompanyDetailSerializer,
    RegisterSerializer,
    ResumeSerializer,
    UserMeSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    API view for registering a new user and sending an email verification link.
    """

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Send verification email (non-blocking: failure is logged, not raised)
        email_sent = send_verification_email(user)

        user_data = UserMeSerializer(user).data
        response_data = {
            "user": user_data,
            "email_verification_sent": email_sent,
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


class VerifyEmailView(APIView):
    """
    API view for verifying a user's email address using a signed token.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        token = request.data.get("token", "")
        if not token:
            return Response(
                {"detail": "Verification token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = verify_token(token)
        if payload is None:
            return Response(
                {"detail": "Invalid or expired verification link. Please request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            user = User.objects.get(pk=payload["user_id"], email=payload["email"])
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if user.is_email_verified:
            return Response(
                {"detail": "Email is already verified."},
                status=status.HTTP_200_OK,
            )

        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        return Response(
            {"detail": "Email verified successfully."},
            status=status.HTTP_200_OK,
        )


class ResendVerificationView(APIView):
    """
    API view for resending the email verification link.
    Accepts either an authenticated request or an email in the request body.
    """

    permission_classes = [AllowAny]
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        # Try authenticated user first, then email from body
        user = None
        if request.user and request.user.is_authenticated:
            user = request.user
        else:
            email = request.data.get("email", "")
            if not email:
                return Response(
                    {"detail": "Email address is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Don't reveal whether email exists — always return success
                return Response(
                    {"detail": "If an account with that email exists, a verification email has been sent."},
                    status=status.HTTP_200_OK,
                )

        if user.is_email_verified:
            return Response(
                {"detail": "Email is already verified."},
                status=status.HTTP_200_OK,
            )

        if not send_verification_email(user):
            return Response(
                {"detail": "We couldn't send the verification email right now. Please try again in a few minutes."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            {"detail": "Verification email sent."},
            status=status.HTTP_200_OK,
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

        if profile.verification_status != VerificationStatus.APPROVED:
            profile.verification_status = VerificationStatus.APPROVED
            profile.save()
            notify_employer_approved(profile)
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

        if profile.verification_status != VerificationStatus.REJECTED:
            profile.verification_status = VerificationStatus.REJECTED
            profile.save()
            notify_employer_rejected(profile)
        serializer = EmployerProfileAdminSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SeekerResumeListCreateView(generics.ListCreateAPIView):
    """
    API view for seekers to list their resumes and upload new resumes (up to 3 max).
    """

    serializer_class = ResumeSerializer
    permission_classes = [IsSeeker]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return Resume.objects.filter(seeker=self.request.user.seeker_profile).order_by("-is_primary", "-created_at")

    def perform_create(self, serializer):
        serializer.save(seeker=self.request.user.seeker_profile)


class SeekerResumeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for seekers to retrieve, update, or delete an individual resume.
    """

    serializer_class = ResumeSerializer
    permission_classes = [IsSeeker]

    def get_queryset(self):
        return Resume.objects.filter(seeker=self.request.user.seeker_profile)

    def perform_destroy(self, instance):
        instance.delete()


class SeekerResumeSetPrimaryView(APIView):
    """
    API view to designate a specific resume as the seeker's primary resume.
    """

    permission_classes = [IsSeeker]

    def post(self, request, pk):
        resume = get_object_or_404(Resume, pk=pk, seeker=request.user.seeker_profile)
        resume.is_primary = True
        resume.save()
        serializer = ResumeSerializer(resume, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicCompanyDetailView(generics.RetrieveAPIView):
    """
    Public API view for retrieving company showcase details and active job postings.
    """

    queryset = EmployerProfile.objects.all()
    serializer_class = PublicCompanyDetailSerializer
    permission_classes = [AllowAny]
