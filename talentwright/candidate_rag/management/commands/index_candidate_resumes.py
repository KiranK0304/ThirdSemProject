"""Management command to backfill candidate resume chunks and embeddings."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from talentwright.candidate_rag.models import CandidateResumeChunk
from talentwright.candidate_rag.services.embeddings import EmbeddingClient
from talentwright.candidate_rag.services.indexer import index_resume_analysis
from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord


class Command(BaseCommand):
    help = "Index structured resume analysis records into candidate resume chunks and embeddings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--job-id",
            type=int,
            default=None,
            help="Filter candidate resumes by specific job ID.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-index applications even if chunks already exist.",
        )
        parser.add_argument(
            "--unindexed-only",
            action="store_true",
            help="Target only completed applications that currently have no chunks (retry failed indexing).",
        )

    def handle(self, *args, **options):
        job_id = options.get("job_id")
        force = options.get("force", False)
        unindexed_only = options.get("unindexed_only", False)

        records_qs = (
            ResumeAnalysisRecord.objects.filter(status=AnalysisStatus.COMPLETED)
            .select_related("application__job", "application__seeker__user")
            .order_by("application__job_id", "application_id")
        )

        if unindexed_only:
            records_qs = records_qs.filter(chunks__isnull=True)

        if job_id:
            records_qs = records_qs.filter(application__job_id=job_id)

        total_records = records_qs.count()
        if total_records == 0:
            self.stdout.write(self.style.WARNING("No completed resume analysis records found to index."))
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Starting indexing for {total_records} completed application(s)..."
            )
        )

        embedding_client = EmbeddingClient()
        indexed_count = 0
        total_chunks = 0
        skipped_count = 0

        for record in records_qs:
            app = record.application
            existing_chunks_count = CandidateResumeChunk.objects.filter(application=app).count()

            if existing_chunks_count > 0 and not force:
                self.stdout.write(
                    f"  [-] Application #{app.id} already has {existing_chunks_count} chunks. (Use --force to re-index)"
                )
                skipped_count += 1
                continue

            try:
                chunks = index_resume_analysis(record, embedding_client=embedding_client)
                total_chunks += len(chunks)
                indexed_count += 1
                cand_name = getattr(record.application.seeker.user, "name", "") or f"App #{app.id}"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  [+] Indexed Application #{app.id} ({cand_name}) -> {len(chunks)} chunks created."
                    )
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(
                        f"  [!] Failed to index Application #{app.id}: {exc}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nIndexing Complete: {indexed_count} indexed, {skipped_count} skipped, {total_chunks} chunks stored."
            )
        )
