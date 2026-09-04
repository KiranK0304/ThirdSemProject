from talentwright.notifications.models import Notification, NotificationType


def notify_employer_approved(profile) -> Notification:
    return Notification.objects.create(
        recipient=profile.user,
        notification_type=NotificationType.EMPLOYER_APPROVED,
        title="Employer profile approved",
        message="Your employer profile has been approved.",
        related_url="/employer/profile",
    )


def notify_employer_rejected(profile) -> Notification:
    return Notification.objects.create(
        recipient=profile.user,
        notification_type=NotificationType.EMPLOYER_REJECTED,
        title="Employer profile rejected",
        message="Your employer profile has been rejected.",
        related_url="/employer/profile",
    )


def notify_application_submitted(application) -> Notification:
    return Notification.objects.create(
        recipient=application.job.employer.user,
        notification_type=NotificationType.APPLICATION_SUBMITTED,
        title="New job application",
        message=f"A new application was submitted for {application.job.title}.",
        related_url=f"/employer/jobs/{application.job_id}/applicants",
    )


def notify_application_status_changed(application) -> Notification:
    status_label = application.get_status_display()
    return Notification.objects.create(
        recipient=application.seeker.user,
        notification_type=NotificationType.APPLICATION_STATUS_CHANGED,
        title="Application status updated",
        message=f"Your application for {application.job.title} is now {status_label.lower()}.",
        related_url=f"/seeker/applications/{application.pk}",
    )
