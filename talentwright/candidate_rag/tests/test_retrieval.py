"""Tests for candidate RAG retrieval service."""

from decimal import Decimal
from unittest.mock import MagicMock
import pytest

from talentwright.applications.models import Application
from talentwright.candidate_rag.models import CandidateResumeChunk
from talentwright.candidate_rag.models import ChunkType
from talentwright.candidate_rag.services.retrieval import search_candidate_chunks
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.fixture
def retrieval_setup(db):
    employer_user = User.objects.create_user(
        email="emp_ret@example.com", password="Password123!"
    )
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    job1 = Job.objects.create(
        employer=employer, title="AI Architect", status=JobStatus.OPEN
    )
    job2 = Job.objects.create(
        employer=employer, title="Frontend Dev", status=JobStatus.OPEN
    )

    # Candidate A (applied to job1) - Strong in PyTorch / AI
    user_a = User.objects.create_user(email="alice@ai.com", name="Alice AI")
    seeker_a = SeekerProfile.objects.create(user=user_a)
    app_a = Application.objects.create(job=job1, seeker=seeker_a)
    rec_a = ResumeAnalysisRecord.objects.create(
        application=app_a,
        status=AnalysisStatus.COMPLETED,
        overall_score=Decimal("94.00"),
        recommendation="STRONG_FIT",
        structured_resume={
            "skills": ["Python", "PyTorch", "Transformers"],
            "total_years_experience": 6.0,
            "summary": "AI researcher specializing in deep learning.",
        },
    )
    # Unit vector pointing primarily along dimension 0
    CandidateResumeChunk.objects.create(
        application=app_a,
        job=job1,
        resume_analysis=rec_a,
        candidate_name="Alice AI",
        chunk_type=ChunkType.WORK_EXPERIENCE,
        content="Lead AI Engineer: Trained large scale models using PyTorch.",
        embedding=[1.0, 0.0, 0.0],
    )

    # Candidate B (applied to job1) - Strong in PostgreSQL / DevOps
    user_b = User.objects.create_user(email="bob@db.com", name="Bob DB")
    seeker_b = SeekerProfile.objects.create(user=user_b)
    app_b = Application.objects.create(job=job1, seeker=seeker_b)
    rec_b = ResumeAnalysisRecord.objects.create(
        application=app_b,
        status=AnalysisStatus.COMPLETED,
        overall_score=Decimal("82.00"),
        recommendation="MODERATE_FIT",
        structured_resume={
            "skills": ["PostgreSQL", "Docker", "Linux"],
            "total_years_experience": 4.0,
            "summary": "Database administrator and DevOps engineer.",
        },
    )
    # Unit vector pointing primarily along dimension 1
    CandidateResumeChunk.objects.create(
        application=app_b,
        job=job1,
        resume_analysis=rec_b,
        candidate_name="Bob DB",
        chunk_type=ChunkType.WORK_EXPERIENCE,
        content="Database Engineer: Tuned PostgreSQL queries and built backups.",
        embedding=[0.0, 1.0, 0.0],
    )

    # Candidate C (applied to job2 - Different Job)
    user_c = User.objects.create_user(email="carol@web.com", name="Carol Web")
    seeker_c = SeekerProfile.objects.create(user=user_c)
    app_c = Application.objects.create(job=job2, seeker=seeker_c)
    rec_c = ResumeAnalysisRecord.objects.create(
        application=app_c,
        status=AnalysisStatus.COMPLETED,
        overall_score=Decimal("90.00"),
        structured_resume={"skills": ["React", "JavaScript"]},
    )
    CandidateResumeChunk.objects.create(
        application=app_c,
        job=job2,
        resume_analysis=rec_c,
        candidate_name="Carol Web",
        chunk_type=ChunkType.WORK_EXPERIENCE,
        content="Frontend Lead: Built React SPAs.",
        embedding=[1.0, 0.0, 0.0],  # Same vector as Alice, but on job2
    )

    return {"job1": job1, "job2": job2, "app_a": app_a, "app_b": app_b}


@pytest.mark.django_db
def test_search_candidate_chunks_semantic_matching(retrieval_setup):
    job1 = retrieval_setup["job1"]

    # Mock query embedding pointing towards dimension 0 (AI/PyTorch)
    mock_client = MagicMock()
    mock_client.get_embedding.return_value = [0.98, 0.02, 0.0]

    results = search_candidate_chunks(
        job_id=job1.id,
        query="PyTorch model training",
        limit=5,
        min_similarity=0.5,
        embedding_client=mock_client,
    )

    # Only Alice should match above 0.5 threshold
    assert len(results) == 1
    top_candidate = results[0]
    assert top_candidate["name"] == "Alice AI"
    assert top_candidate["overall_score"] == 94.0
    assert len(top_candidate["relevant_evidence"]) == 1
    assert "PyTorch" in top_candidate["relevant_evidence"][0]["details"]
    assert top_candidate["relevant_evidence"][0]["section"] == "Work Experience"
    assert "similarity_score" not in top_candidate["relevant_evidence"][0]


@pytest.mark.django_db
def test_search_candidate_chunks_job_isolation(retrieval_setup):
    job1 = retrieval_setup["job1"]

    # Even though Carol on job2 has embedding [1.0, 0.0, 0.0], searching on job1 must NOT return Carol
    mock_client = MagicMock()
    mock_client.get_embedding.return_value = [1.0, 0.0, 0.0]

    results = search_candidate_chunks(
        job_id=job1.id,
        query="React web developer",
        limit=5,
        embedding_client=mock_client,
    )

    candidate_names = [c["name"] for c in results]
    assert "Carol Web" not in candidate_names


@pytest.mark.django_db
def test_search_candidate_chunks_empty_query(retrieval_setup):
    job1 = retrieval_setup["job1"]
    assert search_candidate_chunks(job_id=job1.id, query="") == []
    assert search_candidate_chunks(job_id=job1.id, query="   ") == []


@pytest.mark.django_db
def test_search_candidate_chunks_self_healing_cold_start(db):
    employer_user = User.objects.create_user(email="cold_emp@example.com")
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    job = Job.objects.create(employer=employer, title="Data Scientist", status=JobStatus.OPEN)

    user = User.objects.create_user(email="david@ai.com", name="David Data")
    seeker = SeekerProfile.objects.create(user=user)
    app = Application.objects.create(job=job, seeker=seeker)
    ResumeAnalysisRecord.objects.create(
        application=app,
        status=AnalysisStatus.COMPLETED,
        overall_score=Decimal("88.00"),
        recommendation="STRONG_FIT",
        structured_resume={
            "skills": ["Python", "Pandas", "Scikit-Learn"],
            "summary": "Data scientist with strong Python machine learning background.",
        },
    )

    # Note: CandidateResumeChunk objects are NOT created initially (cold-start scenario)
    assert CandidateResumeChunk.objects.filter(job=job).count() == 0

    mock_client = MagicMock()
    mock_client.get_embedding.return_value = [1.0, 0.0, 0.0]
    # Return batch embeddings for indexer when it runs on-demand
    mock_client.get_embeddings_batch.return_value = [[1.0, 0.0, 0.0]]

    results = search_candidate_chunks(
        job_id=job.id,
        query="Machine Learning",
        limit=5,
        min_similarity=0.5,
        embedding_client=mock_client,
    )

    # Chunks should now be self-healed and created!
    assert CandidateResumeChunk.objects.filter(job=job).count() > 0
    assert len(results) == 1
    assert results[0]["name"] == "David Data"
    assert results[0]["application_id"] == app.id
