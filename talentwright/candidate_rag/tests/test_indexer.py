"""Tests for candidate RAG indexing service and management command."""

from io import StringIO
from unittest.mock import MagicMock
import pytest
from django.core.management import call_command

from talentwright.applications.models import Application
from talentwright.candidate_rag.models import CandidateResumeChunk
from talentwright.candidate_rag.models import ChunkType
from talentwright.candidate_rag.services.indexer import index_resume_analysis
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.fixture
def indexer_setup(db):
    employer_user = User.objects.create_user(
        email="emp_idx@example.com", password="Password123!"
    )
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    job = Job.objects.create(
        employer=employer, title="Python/AI Engineer", status=JobStatus.OPEN
    )

    candidate_user = User.objects.create_user(
        email="alice_idx@example.com", name="Alice Indexer"
    )
    seeker = SeekerProfile.objects.create(user=candidate_user)
    app = Application.objects.create(job=job, seeker=seeker)

    record = ResumeAnalysisRecord.objects.create(
        application=app,
        status=AnalysisStatus.COMPLETED,
        structured_resume={
            "summary": "Specialist in NLP and Python backends.",
            "skills": ["Python", "PyTorch", "Django"],
            "total_years_experience": 4.0,
            "work_experience": [
                {
                    "company": "DeepTech",
                    "title": "ML Engineer",
                    "start_date": "2021-01",
                    "end_date": "Present",
                    "is_current": True,
                    "description": "Trained LLMs using PyTorch.",
                    "technologies": ["Python", "PyTorch"],
                }
            ],
        },
    )

    return {"job": job, "application": app, "record": record}


@pytest.mark.django_db
def test_index_resume_analysis_success(indexer_setup):
    record = indexer_setup["record"]
    app = indexer_setup["application"]
    job = indexer_setup["job"]

    # Mock embedding client
    mock_client = MagicMock()
    # Resume generates 2 chunks: skills_summary and 1 work_experience
    mock_client.get_embeddings_batch.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]

    chunks = index_resume_analysis(record, embedding_client=mock_client)

    assert len(chunks) == 2
    assert CandidateResumeChunk.objects.filter(application=app).count() == 2

    c1, c2 = chunks
    assert c1.job_id == job.id
    assert c1.application_id == app.id
    assert c1.candidate_name == "Alice Indexer"
    assert c1.chunk_type == ChunkType.SKILLS_SUMMARY
    assert c1.embedding == [0.1, 0.2, 0.3]

    assert c2.chunk_type == ChunkType.WORK_EXPERIENCE
    assert c2.embedding == [0.4, 0.5, 0.6]


@pytest.mark.django_db
def test_index_resume_analysis_idempotency(indexer_setup):
    record = indexer_setup["record"]
    app = indexer_setup["application"]

    mock_client = MagicMock()
    mock_client.get_embeddings_batch.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]

    # Index first time
    index_resume_analysis(record, embedding_client=mock_client)
    assert CandidateResumeChunk.objects.filter(application=app).count() == 2

    # Index second time (re-analysis or update)
    index_resume_analysis(record, embedding_client=mock_client)
    # Count should STILL be exactly 2, not 4
    assert CandidateResumeChunk.objects.filter(application=app).count() == 2


@pytest.mark.django_db
def test_index_empty_structured_resume(indexer_setup):
    record = indexer_setup["record"]
    record.structured_resume = {}
    record.save()

    mock_client = MagicMock()
    chunks = index_resume_analysis(record, embedding_client=mock_client)
    assert chunks == []
    mock_client.get_embeddings_batch.assert_not_called()


@pytest.mark.django_db
def test_management_command_index_candidate_resumes(indexer_setup, monkeypatch):
    mock_client = MagicMock()
    mock_client.get_embeddings_batch.return_value = [
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
    ]
    monkeypatch.setattr(
        "talentwright.candidate_rag.management.commands.index_candidate_resumes.EmbeddingClient",
        lambda: mock_client,
    )

    out = StringIO()
    call_command("index_candidate_resumes", stdout=out)
    output = out.getvalue()

    assert "Starting indexing for 1 completed application" in output
    assert "Indexing Complete: 1 indexed" in output
    assert CandidateResumeChunk.objects.count() == 2
