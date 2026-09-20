from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import send_mail

if TYPE_CHECKING:
    from talentwright.applications.models import Application

logger = logging.getLogger(__name__)


def send_application_shortlist_email(application: Application) -> bool:
    """Send an email notification to the job seeker when their application is shortlisted."""
    try:
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
        message = (
            f"Dear {seeker_name},\n\n"
            f"Great news! Your application for the position of \"{job_title}\" at {company_name} "
            f"has been reviewed and you have been shortlisted!\n\n"
            f"The hiring team was impressed with your qualifications and may reach out to schedule next steps.\n\n"
            f"You can review your application status and updates on your dashboard at any time.\n\n"
            f"Best regards,\n"
            f"{company_name} & the TalentWright Team"
        )

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@talentwright.com")
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[seeker_email],
            fail_silently=False,
        )
        logger.info(
            "Shortlist email sent to %s for application #%s",
            seeker_email,
            application.id,
        )
        return True
    except Exception as exc:
        logger.error(
            "Failed to send shortlist email for application #%s: %s",
            application.id,
            exc,
            exc_info=True,
        )
        return False


def send_application_rejection_email(application: Application, note: str = "") -> bool:
    """Send an email notification to the job seeker when their application is rejected,

    optionally including a personal feedback note from the employer.
    """
    try:
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

        note_section = ""
        clean_note = (note or "").strip()
        if clean_note:
            note_section = f"\nNote from the hiring team:\n\"{clean_note}\"\n"

        message = (
            f"Dear {seeker_name},\n\n"
            f"Thank you for your interest in the position of \"{job_title}\" at {company_name} "
            f"and for taking the time to submit your application.\n\n"
            f"After careful consideration, the hiring team has decided not to move forward with your application at this time.{note_section}\n"
            f"We appreciate your effort and interest in {company_name}, and we wish you the very best in your job search and future professional endeavors.\n\n"
            f"Best regards,\n"
            f"{company_name} & the TalentWright Team"
        )

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@talentwright.com")
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[seeker_email],
            fail_silently=False,
        )
        logger.info(
            "Rejection email sent to %s for application #%s",
            seeker_email,
            application.id,
        )
        return True
    except Exception as exc:
        logger.error(
            "Failed to send rejection email for application #%s: %s",
            application.id,
            exc,
            exc_info=True,
        )
        return False
