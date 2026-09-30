from __future__ import annotations

import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

# Token settings
VERIFICATION_SALT = "email-verification"
VERIFICATION_MAX_AGE = 60 * 60 * 24  # 24 hours


def generate_verification_token(user) -> str:
    """Generate a signed, time-limited email verification token."""
    return signing.dumps({"user_id": user.pk, "email": user.email}, salt=VERIFICATION_SALT)


def verify_token(token: str) -> dict | None:
    """Validate a verification token. Returns payload dict or None if invalid/expired."""
    try:
        return signing.loads(token, salt=VERIFICATION_SALT, max_age=VERIFICATION_MAX_AGE)
    except (signing.BadSignature, signing.SignatureExpired):
        return None


def send_verification_email(user) -> bool:
    """Send an email verification link to the user."""
    try:
        if not user.email:
            logger.warning("Cannot send verification email: user %s has no email", user.pk)
            return False

        token = generate_verification_token(user)
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        verification_url = f"{frontend_url}/verify-email?token={token}"

        subject = "Verify your email address — TalentWright"
        html_message = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 16px; color: #1a1a1a;">
  <div style="text-align: center; margin-bottom: 28px;">
    <h1 style="font-size: 22px; font-weight: 600; margin: 0; color: #111;">TalentWright</h1>
  </div>
  <h2 style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">Verify your email address</h2>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">Hi {user.name or 'there'},</p>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">Thanks for creating a TalentWright account! Please verify your email address by clicking the button below.</p>
  <div style="text-align: center; margin: 28px 0;">
    <a href="{verification_url}" style="display: inline-block; background-color: #D97706; color: #fff; text-decoration: none; font-size: 15px; font-weight: 500; padding: 12px 32px; border-radius: 8px;">Verify Email Address</a>
  </div>
  <p style="font-size: 13px; line-height: 1.6; color: #888;">This link will expire in 24 hours. If you didn't create an account, you can safely ignore this email.</p>
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
  <p style="font-size: 12px; color: #aaa; text-align: center;">TalentWright &mdash; Your Career, Simplified</p>
</body>
</html>"""

        plain_message = (
            f"Hi {user.name or 'there'},\n\n"
            f"Thanks for creating a TalentWright account!\n\n"
            f"Please verify your email by visiting this link:\n{verification_url}\n\n"
            f"This link will expire in 24 hours.\n\n"
            f"— TalentWright Team"
        )

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@talentwright.com")
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info("Verification email sent to %s", user.email)
        return True
    except Exception as exc:
        logger.error("Failed to send verification email to %s: %s", user.email, exc, exc_info=True)
        return False
