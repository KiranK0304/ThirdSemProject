from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail

if TYPE_CHECKING:
    from talentwright.applications.models import Application

logger = logging.getLogger(__name__)


def _email_wrapper(
    subject: str,
    body_html: str,
    body_text: str,
    to_email: str,
    sender_name: str | None = None,
    reply_to: list[str] | None = None,
) -> bool:
    """Low-level send helper. Supports dynamic display name and reply-to."""
    try:
        host_user = getattr(settings, "EMAIL_HOST_USER", "")
        default_from = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@talentwright.com")

        if sender_name and host_user:
            from_email = f"{sender_name} <{host_user}>"
        else:
            from_email = default_from

        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=from_email,
            to=[to_email],
            reply_to=reply_to or [],
        )
        msg.attach_alternative(body_html, "text/html")
        msg.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.error("Email send failed to %s: %s", to_email, exc, exc_info=True)
        return False


def _base_html(content: str) -> str:
    """Wrap email content in a clean HTML template."""
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 16px; color: #1a1a1a;">
  <div style="text-align: center; margin-bottom: 28px;">
    <h1 style="font-size: 22px; font-weight: 600; margin: 0; color: #111;">TalentWright</h1>
  </div>
  {content}
  <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
  <p style="font-size: 12px; color: #aaa; text-align: center;">TalentWright &mdash; Your Career, Simplified</p>
</body>
</html>"""


def send_application_shortlist_email(application: Application) -> bool:
    """Send an email notification to the job seeker when their application is shortlisted."""
    seeker_email = application.seeker.user.email
    if not seeker_email:
        logger.warning(
            "Cannot send shortlist email: application %s seeker has no email address",
            application.id,
        )
        return False

    seeker_name = application.seeker.user.name or "Candidate"
    job_title = application.job.title
    employer = getattr(application.job, "employer", None)
    company_name = getattr(employer, "company_name", "") or "The Hiring Team"

    subject = f"Congratulations! You've been shortlisted for {job_title}"

    html_content = f"""\
  <h2 style="font-size: 18px; font-weight: 600; margin-bottom: 12px; color: #15803d;">🎉 You've been shortlisted!</h2>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">Hi {seeker_name},</p>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">Great news! Your application for <strong>{job_title}</strong> at <strong>{company_name}</strong> has been reviewed and you have been <strong>shortlisted</strong>.</p>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">The hiring team was impressed with your qualifications and may reach out to schedule next steps.</p>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">You can review your application status and updates on your dashboard at any time.</p>
  <p style="font-size: 15px; line-height: 1.6; color: #444; margin-top: 20px;">Best regards,<br>{company_name} &amp; the TalentWright Team</p>"""

    plain_message = (
        f"Hi {seeker_name},\n\n"
        f"Great news! Your application for \"{job_title}\" at {company_name} "
        f"has been reviewed and you have been shortlisted!\n\n"
        f"The hiring team was impressed with your qualifications and may reach out to schedule next steps.\n\n"
        f"You can review your application status and updates on your dashboard at any time.\n\n"
        f"Best regards,\n"
        f"{company_name} & the TalentWright Team"
    )

    employer_email = getattr(getattr(employer, "user", None), "email", None)
    sender_name = f"{company_name} via TalentWright" if company_name else "TalentWright"
    reply_to = [employer_email] if employer_email else []

    result = _email_wrapper(
        subject,
        _base_html(html_content),
        plain_message,
        seeker_email,
        sender_name=sender_name,
        reply_to=reply_to,
    )
    if result:
        logger.info("Shortlist email sent to %s for application #%s", seeker_email, application.id)
    return result


def send_application_rejection_email(application: Application, note: str = "") -> bool:
    """Send an email notification to the job seeker when their application is rejected,

    optionally including a personal feedback note from the employer.
    """
    seeker_email = application.seeker.user.email
    if not seeker_email:
        logger.warning(
            "Cannot send rejection email: application %s seeker has no email address",
            application.id,
        )
        return False

    seeker_name = application.seeker.user.name or "Candidate"
    job_title = application.job.title
    employer = getattr(application.job, "employer", None)
    company_name = getattr(employer, "company_name", "") or "The Hiring Team"

    subject = f"Update regarding your application for {job_title}"

    clean_note = (note or "").strip()
    note_html = ""
    note_text = ""
    if clean_note:
        note_html = f"""\
  <div style="background-color: #f8f8f8; border-left: 3px solid #D97706; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
    <p style="font-size: 13px; color: #666; margin: 0 0 4px 0; font-weight: 500;">Note from the hiring team:</p>
    <p style="font-size: 14px; color: #333; margin: 0; font-style: italic;">"{clean_note}"</p>
  </div>"""
        note_text = f"\nNote from the hiring team:\n\"{clean_note}\"\n"

    html_content = f"""\
  <h2 style="font-size: 18px; font-weight: 600; margin-bottom: 12px;">Application Update</h2>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">Hi {seeker_name},</p>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">Thank you for your interest in the position of <strong>{job_title}</strong> at <strong>{company_name}</strong> and for taking the time to submit your application.</p>
  <p style="font-size: 15px; line-height: 1.6; color: #444;">After careful consideration, the hiring team has decided not to move forward with your application at this time.</p>
  {note_html}
  <p style="font-size: 15px; line-height: 1.6; color: #444;">We appreciate your effort and interest in {company_name}, and we wish you the very best in your job search and future professional endeavors.</p>
  <p style="font-size: 15px; line-height: 1.6; color: #444; margin-top: 20px;">Best regards,<br>{company_name} &amp; the TalentWright Team</p>"""

    plain_message = (
        f"Hi {seeker_name},\n\n"
        f"Thank you for your interest in the position of \"{job_title}\" at {company_name} "
        f"and for taking the time to submit your application.\n\n"
        f"After careful consideration, the hiring team has decided not to move forward with your application at this time.{note_text}\n"
        f"We appreciate your effort and interest in {company_name}, and we wish you the very best in your job search and future professional endeavors.\n\n"
        f"Best regards,\n"
        f"{company_name} & the TalentWright Team"
    )

    employer_email = getattr(getattr(employer, "user", None), "email", None)
    sender_name = f"{company_name} via TalentWright" if company_name else "TalentWright"
    reply_to = [employer_email] if employer_email else []

    result = _email_wrapper(
        subject,
        _base_html(html_content),
        plain_message,
        seeker_email,
        sender_name=sender_name,
        reply_to=reply_to,
    )
    if result:
        logger.info("Rejection email sent to %s for application #%s", seeker_email, application.id)
    return result
