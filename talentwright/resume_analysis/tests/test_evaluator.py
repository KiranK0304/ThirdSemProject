"""Tests for evaluation schemas and objective baseline evaluator."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from talentwright.resume_analysis.evaluation_schemas import CriterionEvaluation
from talentwright.resume_analysis.evaluation_schemas import EvaluationScorecard
from talentwright.resume_analysis.evaluation_schemas import JobContext
from talentwright.resume_analysis.schemas import StructuredResume
from talentwright.resume_analysis.services.evaluator import evaluate_resume
from talentwright.resume_analysis.services.llm_client import LLMClient


def test_job_context_typed_dict():
    context: JobContext = {
        "job_id": 42,
        "title": "Senior Python Engineer",
        "description": "Must have 5+ years with Django, PostgreSQL, and Docker.",
        "cover_letter": "I have built large distributed systems with Django.",
    }
    assert context["job_id"] == 42
    assert context["title"] == "Senior Python Engineer"
    assert "Django" in context["description"]
    assert "cover_letter" in context


def test_evaluation_scorecard_defaults():
    scorecard = EvaluationScorecard()
    assert scorecard.overall_score == 0.0
    assert scorecard.recommendation == "MODERATE_FIT"
    assert scorecard.skills_evaluation.score == 0.0
    assert scorecard.experience_evaluation.score == 0.0
    assert scorecard.education_evaluation.score == 0.0
    assert scorecard.strengths == []
    assert scorecard.concerns == []


def test_criterion_evaluation_score_bounds():
    valid = CriterionEvaluation(score=85.5, reasoning="Strong background")
    assert valid.score == 85.5

    with pytest.raises(ValidationError):
        CriterionEvaluation(score=-5.0)

    with pytest.raises(ValidationError):
        CriterionEvaluation(score=105.0)


def test_evaluation_scorecard_serialization_roundtrip():
    payload = {
        "overall_score": 88.0,
        "recommendation": "STRONG_FIT",
        "skills_evaluation": {
            "score": 90.0,
            "reasoning": "Strong match with Python, Django, PostgreSQL",
            "matched_evidence": ["Python", "Django", "PostgreSQL"],
            "gaps": ["Kubernetes"],
        },
        "experience_evaluation": {
            "score": 85.0,
            "reasoning": "6 years experience exceeds 5-year requirement",
            "matched_evidence": ["6.5 years software engineering"],
            "gaps": [],
        },
        "education_evaluation": {
            "score": 90.0,
            "reasoning": "B.S. in Computer Science matches degree requirement",
            "matched_evidence": ["B.S. Computer Science from Stanford"],
            "gaps": [],
        },
        "summary": "Candidate is a strong fit for the Senior Python Engineer role.",
        "strengths": [
            "Extensive Python/Django experience",
            "CS degree from top university",
        ],
        "concerns": ["Lacks hands-on Kubernetes orchestration"],
    }

    scorecard = EvaluationScorecard.model_validate(payload)
    assert scorecard.overall_score == 88.0
    assert scorecard.recommendation == "STRONG_FIT"
    assert len(scorecard.strengths) == 2
    assert scorecard.skills_evaluation.score == 90.0

    dumped = scorecard.model_dump()
    assert dumped["overall_score"] == 88.0
    assert dumped["recommendation"] == "STRONG_FIT"


def test_evaluate_resume_empty_job_context():
    resume = StructuredResume(summary="Developer")
    empty_context: JobContext = {}

    with pytest.raises(
        ValueError, match="must contain at least a title or description"
    ):
        evaluate_resume(resume, empty_context)


def test_calculate_composite_score():
    from talentwright.resume_analysis.services.evaluator import calculate_composite_score

    # 90 * 0.50 + 80 * 0.35 + 70 * 0.15 = 45 + 28 + 10.5 = 83.5
    score, rec = calculate_composite_score(
        skills_score=90.0, experience_score=80.0, education_score=70.0
    )
    assert score == 83.5
    assert rec == "STRONG_FIT"

    # 60 * 0.50 + 60 * 0.35 + 60 * 0.15 = 60.0
    score, rec = calculate_composite_score(
        skills_score=60.0, experience_score=60.0, education_score=60.0
    )
    assert score == 60.0
    assert rec == "MODERATE_FIT"

    # 40 * 0.50 + 40 * 0.35 + 40 * 0.15 = 40.0
    score, rec = calculate_composite_score(
        skills_score=40.0, experience_score=40.0, education_score=40.0
    )
    assert score == 40.0
    assert rec == "WEAK_FIT"


def test_evaluate_resume_success_with_mock_client():
    mock_client = MagicMock(spec=LLMClient)
    # Skills: 90 (45) + Exp: 80 (28) + Edu: 60 (9) = 82.0
    expected_scorecard = EvaluationScorecard(
        overall_score=82.0,
        recommendation="STRONG_FIT",
        skills_evaluation=CriterionEvaluation(score=90.0),
        experience_evaluation=CriterionEvaluation(score=80.0),
        education_evaluation=CriterionEvaluation(score=60.0),
        summary="Candidate meets all baseline technical requirements.",
        strengths=["Strong Python depth"],
        concerns=["No cloud certification"],
    )
    mock_client.generate_structured.return_value = expected_scorecard

    resume = StructuredResume(
        summary="Senior Backend Developer",
        skills=["Python", "Django", "PostgreSQL"],
        total_years_experience=6.0,
    )
    job_context: JobContext = {
        "title": "Senior Backend Developer",
        "description": "Looking for Python / Django specialist with 5+ years experience.",
    }

    result = evaluate_resume(resume, job_context, llm_client=mock_client)

    assert result == expected_scorecard
    assert result.overall_score == 82.0
    assert result.recommendation == "STRONG_FIT"
    mock_client.generate_structured.assert_called_once()
    prompt_used = mock_client.generate_structured.call_args.kwargs["prompt"]
    assert "Senior Backend Developer" in prompt_used
    assert "Looking for Python / Django" in prompt_used
    assert "Candidate Structured Resume:" in prompt_used
