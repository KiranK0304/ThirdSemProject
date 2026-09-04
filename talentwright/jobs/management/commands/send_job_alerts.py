from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from talentwright.jobs.models import AlertFrequency
from talentwright.jobs.models import JobAlert
from talentwright.jobs.services import matching_jobs_for_alert


class Command(BaseCommand):
    help = "Send email alerts for newly matching jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show alerts without sending email.",
        )

    def handle(self, *args, **options):
        now = timezone.now()
        alerts = JobAlert.objects.select_related("seeker__user").filter(is_active=True)
        sent_count = 0

        for alert in alerts:
            interval_days = 1 if alert.frequency == AlertFrequency.DAILY else 7
            interval = timedelta(days=interval_days)
            if alert.last_sent_at and now - alert.last_sent_at < interval:
                continue

            jobs = matching_jobs_for_alert(alert)
            if alert.last_sent_at:
                jobs = jobs.filter(created_at__gt=alert.last_sent_at)
            jobs = list(jobs)
            if not jobs:
                continue

            self.stdout.write(f"{alert.seeker.user.email}: {len(jobs)} matching job(s)")
            if not options["dry_run"]:
                job_lines = "\n".join(self._format_job_line(job) for job in jobs)
                send_mail(
                    subject="New jobs match your Hirely alert",
                    message=f"New jobs matching your alert:\n\n{job_lines}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[alert.seeker.user.email],
                )
                alert.last_sent_at = now
                alert.save(update_fields=["last_sent_at", "updated_at"])
            sent_count += 1

        mode = "Would send" if options["dry_run"] else "Sent"
        self.stdout.write(self.style.SUCCESS(f"{mode} {sent_count} job alert(s)."))

    @staticmethod
    def _format_job_line(job):
        employer = job.employer.company_name or job.employer.user.email
        location = job.location or "Location not specified"
        return f"- {job.title} at {employer} ({location})"
