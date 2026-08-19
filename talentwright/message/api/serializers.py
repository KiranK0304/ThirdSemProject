from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from talentwright.message.models import ChatRequest
from talentwright.message.models import ChatRequestStatus
from talentwright.message.models import Message
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import VerificationStatus


class ChatEmployerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = EmployerProfile
        fields = [
            "id",
            "user_id",
            "user_email",
            "user_name",
            "company_name",
            "website",
            "description",
            "verification_status",
        ]
        read_only_fields = fields


class ChatSeekerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = SeekerProfile
        fields = [
            "id",
            "user_id",
            "user_email",
            "user_name",
            "phone",
            "bio",
        ]
        read_only_fields = fields


class ChatRequestDetailSerializer(serializers.ModelSerializer):
    seeker = ChatSeekerSerializer(read_only=True)
    employer = ChatEmployerSerializer(read_only=True)
    latest_message = serializers.SerializerMethodField()
    unread_messages_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRequest
        fields = [
            "id",
            "seeker",
            "employer",
            "status",
            "initial_message",
            "created_at",
            "updated_at",
            "latest_message",
            "unread_messages_count",
        ]
        read_only_fields = fields

    def get_latest_message(self, obj) -> dict | None:
        last_msg = obj.messages.order_by("-created_at").first()
        if not last_msg:
            return None
        return {
            "id": last_msg.id,
            "sender_id": last_msg.sender_id,
            "sender_name": last_msg.sender.name or last_msg.sender.email,
            "content": last_msg.content,
            "created_at": last_msg.created_at,
            "is_read": last_msg.is_read,
        }

    def get_unread_messages_count(self, obj) -> int:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()


class ChatRequestCreateSerializer(serializers.ModelSerializer):
    employer_id = serializers.PrimaryKeyRelatedField(
        queryset=EmployerProfile.objects.select_related("user"),
        source="employer",
        write_only=True,
    )
    initial_message = serializers.CharField(
        allow_blank=True,
        required=False,
        default="",
    )

    class Meta:
        model = ChatRequest
        fields = [
            "id",
            "employer_id",
            "initial_message",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]

    def validate_employer_id(self, employer):
        if employer.verification_status != VerificationStatus.APPROVED:
            err_msg = "Chat requests can only be sent to verified employers."
            raise serializers.ValidationError(err_msg)
        return employer

    def validate(self, attrs):
        seeker = self.context.get("seeker")
        employer = attrs.get("employer")

        if not seeker:
            err_msg = "Only job seekers can create chat requests."
            raise serializers.ValidationError({"non_field_errors": [err_msg]})

        if employer and seeker.user_id == employer.user_id:
            err_msg = "You cannot send a chat request to yourself."
            raise serializers.ValidationError({"employer_id": [err_msg]})

        existing = ChatRequest.objects.filter(seeker=seeker, employer=employer).first()
        if existing and existing.status in [
            ChatRequestStatus.PENDING,
            ChatRequestStatus.APPROVED,
        ]:
            err_msg = (
                f"You already have a request with this employer ({existing.status})."
            )
            raise serializers.ValidationError({"non_field_errors": [err_msg]})

        chat_request = ChatRequest(
            seeker=seeker,
            employer=employer,
            initial_message=attrs.get("initial_message", ""),
        )
        try:
            chat_request.full_clean(
                exclude=["id", "status", "created_at", "updated_at"],
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        return attrs

    def create(self, validated_data):
        seeker = self.context["seeker"]
        employer = validated_data["employer"]
        initial_message = validated_data.get("initial_message", "")

        with transaction.atomic():
            chat_req, _ = ChatRequest.objects.update_or_create(
                seeker=seeker,
                employer=employer,
                defaults={
                    "status": ChatRequestStatus.PENDING,
                    "initial_message": initial_message,
                },
            )
            return chat_req


class ChatRequestStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRequest
        fields = [
            "id",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_status(self, value):
        allowed_statuses = [
            ChatRequestStatus.APPROVED,
            ChatRequestStatus.REJECTED,
        ]
        if value not in allowed_statuses:
            err_msg = (
                f"Invalid status update. Choose one of: {', '.join(allowed_statuses)}."
            )
            raise serializers.ValidationError(err_msg)
        return value


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)
    sender_email = serializers.EmailField(source="sender.email", read_only=True)
    sender_name = serializers.CharField(source="sender.name", read_only=True)
    is_from_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "chat_request",
            "sender_id",
            "sender_email",
            "sender_name",
            "content",
            "is_read",
            "is_from_me",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "chat_request",
            "sender_id",
            "sender_email",
            "sender_name",
            "is_read",
            "is_from_me",
            "created_at",
        ]

    def get_is_from_me(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.sender_id == request.user.id


class MessageCreateSerializer(serializers.ModelSerializer):
    content = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = Message
        fields = [
            "id",
            "content",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "is_read", "created_at"]

    def validate(self, attrs):
        chat_request = self.context.get("chat_request")
        user = self.context.get("request").user

        if not chat_request:
            err_msg = "Chat request context is missing."
            raise serializers.ValidationError({"non_field_errors": [err_msg]})

        if chat_request.status != ChatRequestStatus.APPROVED:
            err_msg = "Messages can only be sent in approved conversations."
            raise serializers.ValidationError({"non_field_errors": [err_msg]})

        allowed_user_ids = {chat_request.seeker.user_id, chat_request.employer.user_id}
        if user.id not in allowed_user_ids:
            err_msg = "You are not a participant in this conversation."
            raise serializers.ValidationError({"non_field_errors": [err_msg]})

        return attrs

    def create(self, validated_data):
        chat_request = self.context["chat_request"]
        user = self.context["request"].user
        return Message.objects.create(
            chat_request=chat_request,
            sender=user,
            content=validated_data["content"],
        )
