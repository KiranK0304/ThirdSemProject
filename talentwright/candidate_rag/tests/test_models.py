"""Tests for candidate_rag database models."""

import pytest
from django.db.models import CASCADE

from talentwright.applications.models import Application
from talentwright.candidate_rag.models import CandidateResumeChunk
from talentwright.candidate_rag.models import ChunkType
from talentwright.jobs.models import Job
from talentwright.jobs.models import JobStatus
from talentwright.resume_analysis.models import AnalysisStatus
from talentwright.resume_analysis.models import ResumeAnalysisRecord
from talentwright.users.models import EmployerProfile
from talentwright.users.models import SeekerProfile
from talentwright.users.models import User
from talentwright.users.models import VerificationStatus


@pytest.fixture
def rag_model_setup(db):
    employer_user = User.objects.create_user(
        email="emp_rag@example.com", password="Password123!"
    )
    employer = EmployerProfile.objects.create(
        user=employer_user, verification_status=VerificationStatus.APPROVED
    )
    job = Job.objects.create(
        employer=employer, title="Senior Backend Engineer", status=JobStatus.OPEN
    )

    candidate_user = User.objects.create_user(
        email="cand_rag@example.com", name="Jane Doe"
    )
    seeker = SeekerProfile.objects.create(user=candidate_user)
    application = Application.objects.create(job=job, seeker=seeker)

    analysis_record = ResumeAnalysisRecord.objects.create(
        application=application,
        status=AnalysisStatus.COMPLETED,
        structured_resume={"skills": ["Python", "FastAPI"]},
    )

    return {
        "job": job,
        "application": application,
        "analysis_record": analysis_record,
        "candidate_user": candidate_user,
    }


@pytest.mark.django_db
def test_create_candidate_resume_chunk(rag_model_setup):
    job = rag_model_setup["job"]
    app = rag_model_setup["application"]
    record = rag_model_setup["analysis_record"]

    chunk = CandidateResumeChunk.objects.create(
        application=app,
        job=job,
        resume_analysis=record,
        candidate_name="Jane Doe",
        chunk_type=ChunkType.WORK_EXPERIENCE,
        content="Built microservices in Python and FastAPI at Tech Corp.",
        metadata={"company": "Tech Corp", "role": "Senior Engineer"},
        embedding=[0.1, 0.2, 0.3],
    )

    assert chunk.id is not None
    assert chunk.candidate_name == "Jane Doe"
    assert chunk.chunk_type == ChunkType.WORK_EXPERIENCE
    assert chunk.job_id == job.id
    assert chunk.application_id == app.id
    assert chunk.resume_analysis_id == record.id
    assert chunk.embedding == [0.1, 0.2, 0.3]
    assert str(chunk) == f"Jane Doe - [WORK_EXPERIENCE] (Job #{job.id})"


@pytest.mark.django_db
def test_cascade_delete_application(rag_model_setup):
    job = rag_model_setup["job"]
    app = rag_model_setup["application"]
    record = rag_model_setup["analysis_record"]

    CandidateResumeChunk.objects.create(
        application=app,
        job=job,
        resume_analysis=record,
        candidate_name="Jane Doe",
        chunk_type=ChunkType.SKILLS_SUMMARY,
        content="Skills: Python, FastAPI",
    )

    assert CandidateResumeChunk.objects.filter(application=app).count() == 1

    # Deleting application should cascade delete the chunks
    app.delete()
    assert CandidateResumeChunk.objects.filter(job=job).count() == 0
