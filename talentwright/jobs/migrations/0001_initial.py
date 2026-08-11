# Generated manually for the initial Job model.

from django.db import migrations
from django.db import models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("users", "0002_employerprofile_seekerprofile"),
    ]

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(max_length=255, verbose_name="Job title"),
                ),
                (
                    "description",
                    models.TextField(verbose_name="Job description"),
                ),
                (
                    "location",
                    models.CharField(blank=True, max_length=255, verbose_name="Location"),
                ),
                (
                    "employment_type",
                    models.CharField(
                        choices=[
                            ("FULL_TIME", "Full time"),
                            ("PART_TIME", "Part time"),
                            ("CONTRACT", "Contract"),
                            ("INTERNSHIP", "Internship"),
                            ("TEMPORARY", "Temporary"),
                            ("FREELANCE", "Freelance"),
                        ],
                        max_length=20,
                        verbose_name="Employment type",
                    ),
                ),
                (
                    "salary_min",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="Minimum salary"),
                ),
                (
                    "salary_max",
                    models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="Maximum salary"),
                ),
                (
                    "salary_currency",
                    models.CharField(default="USD", max_length=3, verbose_name="Salary currency"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("OPEN", "Open"),
                            ("CLOSED", "Closed"),
                            ("ARCHIVED", "Archived"),
                        ],
                        default="DRAFT",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="jobs",
                        to="users.employerprofile",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["employer", "status"], name="jobs_job_employe_6f0f57_idx"),
                    models.Index(fields=["status", "created_at"], name="jobs_job_status__0a3fb0_idx"),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=(
                            models.Q(salary_min__isnull=True)
                            | models.Q(salary_max__isnull=True)
                            | models.Q(salary_min__lte=models.F("salary_max"))
                        ),
                        name="jobs_job_salary_range_valid",
                    ),
                ],
            },
        ),
    ]
