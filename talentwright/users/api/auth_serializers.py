from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from talentwright.users.models import EmployerProfile, SeekerProfile

User = get_user_model()


class EmployerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for EmployerProfile model.
    """
    class Meta:
        model = EmployerProfile
        fields = [
            "id",
            "company_name",
            "website",
            "description",
            "verification_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "verification_status", "created_at", "updated_at"]


class SeekerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for SeekerProfile model.
    """
    class Meta:
        model = SeekerProfile
        fields = ["id", "phone", "bio", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class RegisterSerializer(serializers.ModelSerializer):
    """
    Minimal Registration Serializer: accepts strictly core credentials
    and creates the corresponding empty profile atomically.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )
    account_type = serializers.ChoiceField(
        choices=["EMPLOYER", "SEEKER"],
        write_only=True,
        required=True,
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "password",
            "password_confirm",
            "account_type",
        ]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Password fields do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        account_type = validated_data.pop("account_type")

        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                name=validated_data.get("name", ""),
                is_active=True,
            )
            if account_type == "EMPLOYER":
                EmployerProfile.objects.create(user=user)
            elif account_type == "SEEKER":
                SeekerProfile.objects.create(user=user)
            return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom SimpleJWT login serializer returning user profile details and account type.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "email": self.user.email,
            "name": self.user.name,
            "account_type": self.user.account_type,
        }
        return data


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for validating refresh token to be blacklisted.
    """
    refresh = serializers.CharField(required=True)


class UserMeSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing and updating current user and profile details.
    """
    account_type = serializers.CharField(read_only=True)
    employer_profile = EmployerProfileSerializer(required=False, allow_null=True)
    seeker_profile = SeekerProfileSerializer(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "account_type",
            "is_active",
            "date_joined",
            "employer_profile",
            "seeker_profile",
        ]
        read_only_fields = ["id", "email", "account_type", "is_active", "date_joined"]

    def update(self, instance, validated_data):
        employer_profile_data = validated_data.pop("employer_profile", None)
        seeker_profile_data = validated_data.pop("seeker_profile", None)

        instance.name = validated_data.get("name", instance.name)
        instance.save()

        if employer_profile_data and hasattr(instance, "employer_profile"):
            profile = instance.employer_profile
            profile.company_name = employer_profile_data.get("company_name", profile.company_name)
            profile.website = employer_profile_data.get("website", profile.website)
            profile.description = employer_profile_data.get("description", profile.description)
            profile.save()

        if seeker_profile_data and hasattr(instance, "seeker_profile"):
            profile = instance.seeker_profile
            profile.phone = seeker_profile_data.get("phone", profile.phone)
            profile.bio = seeker_profile_data.get("bio", profile.bio)
            profile.save()

        return instance


class EmployerProfileAdminSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Admin Employer Management.
    """
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = EmployerProfile
        fields = [
            "id",
            "user",
            "user_email",
            "user_name",
            "company_name",
            "website",
            "description",
            "verification_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

