from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CASCADE
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import ForeignKey
from django.db.models import TextChoices
from django.db.models import TextField
from django.db.models import UniqueConstraint
from django.utils.translation import gettext_lazy as _

from talentwright.users.models import VerificationStatus


class ChatRequestStatus(TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class ChatRequest(models.Model):
    seeker = ForeignKey(
        "users.SeekerProfile",
        on_delete=CASCADE,
        related_name="chat_requests",
    )
    employer = ForeignKey(
        "users.EmployerProfile",
        on_delete=CASCADE,
        related_name="chat_requests",
    )
    status = CharField(
        _("Status"),
        max_length=20,
        choices=ChatRequestStatus.choices,
        default=ChatRequestStatus.PENDING,
    )
    initial_message = TextField(_("Initial message"), blank=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            UniqueConstraint(
                fields=["seeker", "employer"],
                name="message_chatrequest_seeker_employer_unique",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"ChatRequest from {self.seeker_id} to {self.employer_id} "
            f"[{self.status}]"
        )

    def clean(self):
        super().clean()
        errors: dict[str, str] = {}
        if self.employer_id:
            if self.employer.verification_status != VerificationStatus.APPROVED:
                errors["employer"] = _(
                    "Chat requests can only be sent to verified employers.",
                )
        if self.seeker_id and self.employer_id:
            if self.seeker.user_id == self.employer.user_id:
                errors["employer"] = _("You cannot send a chat request to yourself.")
        if errors:
            raise ValidationError(errors)


class Message(models.Model):
    chat_request = ForeignKey(
        "message.ChatRequest",
        on_delete=CASCADE,
        related_name="messages",
    )
    sender = ForeignKey(
        "users.User",
        on_delete=CASCADE,
        related_name="sent_messages",
    )
    content = TextField(_("Message content"))
    is_read = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Message by {self.sender_id} in ChatRequest {self.chat_request_id}"

    def clean(self):
        super().clean()
        if self.chat_request_id:
            if self.chat_request.status != ChatRequestStatus.APPROVED:
                msg = _("Messages can only be sent in approved chat requests.")
                raise ValidationError({"chat_request": msg})
            if self.sender_id:
                allowed_user_ids = {
                    self.chat_request.seeker.user_id,
                    self.chat_request.employer.user_id,
                }
                if self.sender_id not in allowed_user_ids:
                    msg = _("Sender must be a participant in this conversation.")
                    raise ValidationError({"sender": msg})
