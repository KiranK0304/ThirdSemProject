"""Tests for semantic resume chunker."""

import pytest

from talentwright.candidate_rag.models import ChunkType
from talentwright.candidate_rag.services.chunker import generate_resume_chunks


def test_generate_resume_chunks_full():
    structured_resume = {
        "summary": "Experienced Python and AI engineer specializing in NLP.",
        "skills": ["Python", "FastAPI", "PyTorch", "Docker"],
        "total_years_experience": 5.0,
        "work_experience": [
            {
                "company": "AI Labs",
                "title": "Senior AI Engineer",
                "start_date": "2022-01",
                "end_date": "Present",
                "is_current": True,
                "description": "Architected distributed model serving infrastructure with PyTorch.",
                "technologies": ["Python", "PyTorch", "Kubernetes"],
            },
            {
                "company": "Startup Inc",
                "title": "Backend Developer",
                "start_date": "2019-06",
                "end_date": "2021-12",
                "is_current": False,
                "description": "Built REST APIs with Django and PostgreSQL.",
                "technologies": ["Python", "Django", "PostgreSQL"],
            },
        ],
        "projects": [
            {
                "title": "RAG Chatbot",
                "technologies": ["LangChain", "OpenAI", "FastAPI"],
                "description": "Open-source RAG implementation for legal contracts.",
            }
        ],
        "education": [
            {
                "degree": "B.S.",
                "field_of_study": "Computer Science",
                "institution": "State University",
                "graduation_year": "2019",
            }
        ],
        "certifications": [
            {
                "name": "AWS Certified Solutions Architect",
                "issuer": "Amazon Web Services",
            }
        ],
    }

    chunks = generate_resume_chunks(structured_resume, candidate_name="Alice Smith")

    # Should produce 5 chunks: 1 skills/summary, 2 work experience, 1 project, 1 edu/cert
    assert len(chunks) == 5

    types = [c["chunk_type"] for c in chunks]
    assert types == [
        ChunkType.SKILLS_SUMMARY,
        ChunkType.WORK_EXPERIENCE,
        ChunkType.WORK_EXPERIENCE,
        ChunkType.PROJECT,
        ChunkType.EDUCATION_CERTIFICATIONS,
    ]

    # Verify skills chunk content
    skills_chunk = chunks[0]
    assert "Alice Smith" in skills_chunk["content"]
    assert "PyTorch" in skills_chunk["content"]
    assert skills_chunk["metadata"]["total_years_experience"] == 5.0
    assert "Python" in skills_chunk["metadata"]["skills"]

    # Verify work experience chunk
    exp1_chunk = chunks[1]
    assert "AI Labs" in exp1_chunk["content"]
    assert "Senior AI Engineer" in exp1_chunk["content"]
    assert "PyTorch" in exp1_chunk["content"]
    assert exp1_chunk["metadata"]["company"] == "AI Labs"
    assert exp1_chunk["metadata"]["is_current"] is True

    # Verify project chunk
    proj_chunk = chunks[3]
    assert "RAG Chatbot" in proj_chunk["content"]
    assert "LangChain" in proj_chunk["metadata"]["technologies"]

    # Verify education and cert chunk
    edu_chunk = chunks[4]
    assert "State University" in edu_chunk["content"]
    assert "AWS Certified Solutions Architect" in edu_chunk["content"]


def test_generate_resume_chunks_empty():
    assert generate_resume_chunks({}) == []
    assert generate_resume_chunks({"summary": "", "skills": []}) == []
