from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for API User Registration.
    Bypasses email verification and enforces standard Django password validation rules.
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

    class Meta:
        model = User
        fields = ["id", "email", "name", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Password fields do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            name=validated_data.get("name", ""),
            is_active=True,
        )
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom SimpleJWT login serializer that returns user profile details alongside access/refresh tokens.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = {
            "id": self.user.id,
            "email": self.user.email,
            "name": self.user.name,
        }
        return data


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for validating refresh token to be blacklisted.
    """
    refresh = serializers.CharField(required=True)


class UserMeSerializer(serializers.ModelSerializer):
    """
    Serializer for the current authenticated user's profile details.
    """
    class Meta:
        model = User
        fields = ["id", "email", "name", "is_active", "date_joined"]
        read_only_fields = ["id", "email", "is_active", "date_joined"]
