"""Tests for resume_analysis Pydantic schemas."""

from talentwright.resume_analysis.schemas import CandidateContact
from talentwright.resume_analysis.schemas import Certification
from talentwright.resume_analysis.schemas import Education
from talentwright.resume_analysis.schemas import ProjectItem
from talentwright.resume_analysis.schemas import StructuredResume
from talentwright.resume_analysis.schemas import WorkExperience


def test_candidate_contact_defaults():
    contact = CandidateContact()
    assert contact.name == ""
    assert contact.email == ""
    assert contact.phone == ""
    assert contact.location == ""
    assert contact.linkedin_url == ""
    assert contact.github_url == ""
    assert contact.portfolio_url == ""


def test_work_experience_defaults_and_populated():
    exp = WorkExperience(
        company="Acme Corp",
        title="Senior Python Engineer",
        start_date="2020-01",
        end_date="Present",
        is_current=True,
        description="Architected backend microservices",
        technologies=["Python", "Django", "Docker", "PostgreSQL"],
    )
    assert exp.company == "Acme Corp"
    assert exp.title == "Senior Python Engineer"
    assert exp.is_current is True
    assert len(exp.technologies) == 4
    assert "Django" in exp.technologies


def test_education_defaults_and_populated():
    edu = Education(
        institution="MIT",
        degree="B.S.",
        field_of_study="Computer Science",
        graduation_year="2020",
        gpa="3.9",
    )
    assert edu.institution == "MIT"
    assert edu.degree == "B.S."
    assert edu.field_of_study == "Computer Science"


def test_project_item_and_certification():
    proj = ProjectItem(
        title="Resume Parser",
        description="LLM powered extraction",
        technologies=["Python", "OpenAI"],
        link="https://github.com/example/resume-parser",
    )
    assert proj.title == "Resume Parser"
    assert len(proj.technologies) == 2

    cert = Certification(
        name="AWS Certified Solutions Architect",
        issuer="Amazon Web Services",
        issue_date="2023",
    )
    assert cert.name == "AWS Certified Solutions Architect"
    assert cert.issuer == "Amazon Web Services"


def test_structured_resume_serialization_roundtrip():
    data = {
        "contact": {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "phone": "+1-555-0199",
            "location": "San Francisco, CA",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "github_url": "https://github.com/janedoe",
            "portfolio_url": "https://janedoe.dev",
        },
        "summary": "Experienced Full Stack Engineer with 6+ years in Python and React.",
        "skills": ["Python", "Django", "React", "PostgreSQL", "Docker", "AWS"],
        "total_years_experience": 6.5,
        "work_experience": [
            {
                "company": "Tech Innovations Inc.",
                "title": "Lead Software Engineer",
                "start_date": "2021-03",
                "end_date": "Present",
                "is_current": True,
                "description": "Led team of 5 backend developers building scalable SaaS APIs.",
                "technologies": ["Python", "Django", "AWS", "Redis"],
            },
        ],
        "education": [
            {
                "institution": "Stanford University",
                "degree": "B.S.",
                "field_of_study": "Computer Science",
                "graduation_year": "2019",
                "gpa": "3.85",
            },
        ],
        "projects": [
            {
                "title": "AutoML Pipeline",
                "description": "Automated data pipeline using Celery and Pandas",
                "technologies": ["Python", "Pandas", "Docker"],
                "link": "https://github.com/janedoe/automl",
            },
        ],
        "certifications": [
            {
                "name": "CKA: Certified Kubernetes Administrator",
                "issuer": "CNCF",
                "issue_date": "2022-11",
            },
        ],
    }

    resume = StructuredResume.model_validate(data)
    assert resume.contact.name == "Jane Doe"
    assert resume.total_years_experience == 6.5
    assert len(resume.skills) == 6
    assert len(resume.work_experience) == 1
    assert resume.work_experience[0].company == "Tech Innovations Inc."

    dumped = resume.model_dump()
    assert dumped["contact"]["email"] == "jane@example.com"
    assert dumped["skills"] == [
        "Python",
        "Django",
        "React",
        "PostgreSQL",
        "Docker",
        "AWS",
    ]


def test_structured_resume_empty_defaults():
    resume = StructuredResume()
    assert resume.contact.name == ""
    assert resume.summary == ""
    assert resume.skills == []
    assert resume.total_years_experience == 0.0
    assert resume.work_experience == []
    assert resume.education == []
    assert resume.projects == []
    assert resume.certifications == []
