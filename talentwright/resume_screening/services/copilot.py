"""AI Recruiter Agent Copilot service.

Provides context-aware candidate intelligence, side-by-side candidate comparisons,
tailored interview question generation, outreach email drafts, and direct actionable
shortcuts for recruiters.
"""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from talentwright.resume_screening.models import CandidateScreeningRecord
from talentwright.resume_screening.models import JobRankingSnapshot
from talentwright.resume_screening.schemas import CopilotAction
from talentwright.resume_screening.schemas import CopilotMessage
from talentwright.resume_screening.schemas import CopilotResponse
from talentwright.resume_screening.services.llm_provider import LLMProviderError
from talentwright.resume_screening.services.llm_provider import get_llm_provider
from talentwright.resume_screening.services.weights import get_job_weights

if TYPE_CHECKING:
    from talentwright.jobs.models import Job

logger = logging.getLogger(__name__)


def build_recruiter_agent_context(job: Job) -> dict:
    """Collect all job details, ranked candidates, and resume dossiers."""
    weights, _ = get_job_weights(job)

    snapshot = (
        JobRankingSnapshot.objects.filter(job=job)
        .order_by("-created_at")
        .first()
    )
    ranked_candidates = snapshot.ranked_candidates if snapshot else []

    # Map screening records for deep resume details
    records = CandidateScreeningRecord.objects.filter(job=job).select_related("application")
    records_by_app_id = {rec.application_id: rec for rec in records}

    candidates_context = []
    for cand in ranked_candidates[:10]:  # Top 10 for context window efficiency
        app_id = cand.get("application_id")
        rec = records_by_app_id.get(app_id)
        resume_data = rec.structured_resume if rec and rec.structured_resume else {}

        # Extract concise work experience and skills
        skills = resume_data.get("skills", [])
        experience = resume_data.get("experience", [])
        exp_summary = []
        for exp in experience[:3]:
            role = exp.get("title", "")
            comp = exp.get("company", "")
            desc = exp.get("description", "")
            exp_summary.append(f"{role} at {comp}: {desc[:120]}..." if desc else f"{role} at {comp}")

        candidates_context.append({
            "rank": cand.get("rank"),
            "application_id": app_id,
            "name": cand.get("candidate_name"),
            "email": cand.get("candidate_email"),
            "final_score": cand.get("final_score"),
            "criteria_scores": cand.get("criteria_scores", {}),
            "reasons": {
                crit: detail.get("reason", "")
                for crit, detail in cand.get("criteria_details", {}).items()
            },
            "skills": skills[:10],
            "experience_highlights": exp_summary,
        })

    return {
        "job_id": job.id,
        "job_title": job.title,
        "job_description": (job.description or "")[:500],
        "job_requirements": getattr(job, "requirements", "")[:400],
        "weights": weights,
        "total_ranked": len(ranked_candidates),
        "candidates": candidates_context,
    }


def _build_system_prompt(context: dict) -> str:
    """Build the system prompt containing deep candidate intelligence."""
    job_title = context.get("job_title", "Unknown Role")
    job_desc = context.get("job_description", "")
    weights = context.get("weights", {})
    candidates = context.get("candidates", [])

    candidates_text_blocks = []
    for c in candidates:
        scores_str = ", ".join(f"{k}: {v}/100" for k, v in c.get("criteria_scores", {}).items())
        reasons_str = "; ".join(f"{k}: {r}" for k, r in c.get("reasons", {}).items())
        skills_str = ", ".join(c.get("skills", []))
        exp_str = " | ".join(c.get("experience_highlights", []))

        block = (
            f"- Rank #{c['rank']}: **{c['name']}** (App ID: {c['application_id']})\n"
            f"  Final Match Score: {c['final_score']}%\n"
            f"  Criteria Scores: {scores_str}\n"
            f"  Skills: {skills_str or 'N/A'}\n"
            f"  Experience: {exp_str or 'N/A'}\n"
            f"  AI Screening Evidence: {reasons_str}"
        )
        candidates_text_blocks.append(block)

    candidates_text = "\n\n".join(candidates_text_blocks) or "No ranked candidates available yet."

    return (
        f"You are the TalentWright AI Recruiter Copilot — an expert, objective talent intelligence advisor.\n"
        f"You are assisting a hiring manager for the position: '{job_title}'.\n\n"
        f"JOB OVERVIEW:\n{job_desc}\n\n"
        f"EVALUATION CRITERIA WEIGHTS:\n{weights}\n\n"
        f"RANKED CANDIDATE POOL (Evaluated against resume evidence):\n"
        f"{candidates_text}\n\n"
        f"COPILOT INSTRUCTIONS & RULES:\n"
        f"1. STRICT RELEVANCE POLICY: You are exclusively a recruitment, candidate evaluation, and hiring intelligence assistant for the job '{job_title}'. ONLY answer questions directly related to this job position, its requirements, candidates, evaluations, resumes, screening criteria, interview preparation, outreach messaging, or hiring decisions.\n"
        f"2. OUT-OF-SCOPE REFUSAL: If the user asks ANY question that is outside the scope of recruitment, hiring, this job position, or the candidates (for example: pop culture, movies, general trivia, politics, creative writing, homework help, coding challenges unrelated to evaluating candidates, or general chit-chat), politely but firmly decline to answer. State that you are the TalentWright AI Recruiter Copilot specialized solely in candidate screening, evaluation, and hiring for '{job_title}', and prompt them to ask a question related to the job or candidate pool.\n"
        f"3. Be concise, highly professional, analytical, and structured in your answers.\n"
        f"4. Use Markdown: headers (###), bullet points, and bold text for clarity.\n"
        f"5. Always reference specific candidate names, scores, and factual project/work evidence from the candidate pool.\n"
        f"6. If asked to compare candidates, highlight key differences in experience, strengths, trade-offs, and recommend the best fit.\n"
        f"7. If asked for interview questions, generate 3-5 deep, specific technical and behavioral questions tailored to probe that candidate's background and potential gaps.\n"
        f"8. If asked to draft outreach or interview invitations, write complete, personalized, polished email templates referencing the candidate's exact achievements.\n"
        f"9. If you recommend shortlisting a candidate, mention them clearly by name."
    )


def _detect_suggested_actions(
    reply_text: str,
    user_query: str,
    candidates: list[dict],
) -> list[CopilotAction]:
    """Detect actionable opportunities in the copilot response."""
    actions: list[CopilotAction] = []
    seen_apps = set()

    # 1. Detect candidate shortlist suggestions
    for c in candidates:
        name = c.get("name", "")
        app_id = c.get("application_id")
        if not name or not app_id or app_id in seen_apps:
            continue

        # If name is prominently mentioned in reply and reply suggests advancing/shortlisting
        name_in_reply = re.search(rf"\b{re.escape(name)}\b", reply_text, re.IGNORECASE)
        name_in_query = re.search(rf"\b{re.escape(name)}\b", user_query, re.IGNORECASE)

        if name_in_reply or (name_in_query and len(candidates) <= 2):
            actions.append(
                CopilotAction(
                    action_type="shortlist",
                    label=f"Shortlist {name}",
                    application_id=app_id,
                    candidate_name=name,
                )
            )
            seen_apps.add(app_id)
            if len(actions) >= 3:
                break

    # 2. Detect if reply contains an email draft or interview questions to copy
    has_email = any(term in reply_text.lower() for term in ["subject:", "dear ", "hi ", "interview invitation"])
    has_questions = any(term in reply_text.lower() for term in ["question 1", "interview questions", "probing question", "technical questions:"])

    if has_email:
        actions.append(
            CopilotAction(
                action_type="copy_text",
                label="📋 Copy Email Draft",
                payload=reply_text,
            )
        )
    elif has_questions:
        actions.append(
            CopilotAction(
                action_type="copy_text",
                label="📋 Copy Interview Questions",
                payload=reply_text,
            )
        )

    return actions


def _generate_fallback_response(user_query: str, context: dict) -> CopilotResponse:
    """Deterministic fallback if LLM provider is unreachable."""
    candidates = context.get("candidates", [])
    job_title = context.get("job_title", "the role")

    if not candidates:
        return CopilotResponse(
            reply=f"### AI Recruiter Copilot Status\n\nNo candidates have been evaluated yet for **{job_title}**. Please run candidate shortlisting first using the **Run AI Shortlisting** button.",
            suggested_actions=[],
        )

    top_candidate = candidates[0]
    top_name = top_candidate.get("name", "Top Candidate")
    top_score = top_candidate.get("final_score", 0)

    lower_query = user_query.lower()

    if "compare" in lower_query and len(candidates) >= 2:
        c1, c2 = candidates[0], candidates[1]
        reply = (
            f"### Comparative Evaluation: {c1['name']} vs {c2['name']}\n\n"
            f"Based on objective resume screening for **{job_title}**:\n\n"
            f"- **{c1['name']} (Rank #1, {c1['final_score']}% Match)**\n"
            f"  - **Key Strengths:** Leading score in Experience ({c1.get('criteria_scores', {}).get('experience', 'N/A')}/100) and Skills ({c1.get('criteria_scores', {}).get('skills', 'N/A')}/100).\n"
            f"  - **Profile:** {', '.join(c1.get('skills', [])[:5])}.\n\n"
            f"- **{c2['name']} (Rank #2, {c2['final_score']}% Match)**\n"
            f"  - **Key Strengths:** High technical alignment with Skills ({c2.get('criteria_scores', {}).get('skills', 'N/A')}/100).\n"
            f"  - **Profile:** {', '.join(c2.get('skills', [])[:5])}.\n\n"
            f"**Recommendation:** {c1['name']} provides the strongest overall balance of hands-on architectural experience and verified project deliverables."
        )
        actions = [
            CopilotAction(action_type="shortlist", label=f"Shortlist {c1['name']}", application_id=c1["application_id"], candidate_name=c1["name"]),
            CopilotAction(action_type="shortlist", label=f"Shortlist {c2['name']}", application_id=c2["application_id"], candidate_name=c2["name"]),
        ]
    elif "question" in lower_query or "interview" in lower_query:
        reply = (
            f"### Tailored Interview Questions for {top_name}\n\n"
            f"Here are targeted technical and architectural questions designed for {top_name} (Rank #1, {top_score}% Match):\n\n"
            f"1. **Architecture & Scalability:** You highlighted experience building distributed services. How did you handle data consistency and caching under high traffic?\n"
            f"2. **Core Tech Stack:** Walk me through your most complex Python/React project. What architectural trade-offs did you make between frontend performance and backend API design?\n"
            f"3. **Code Quality & Mentorship:** How do you approach automated testing and code reviews when balancing tight sprint deadlines?\n"
            f"4. **Deep-Dive Scenario:** If you were tasked with migrating a legacy service into microservices for our team, what would your step-by-step rollout plan be?"
        )
        actions = [
            CopilotAction(action_type="copy_text", label="📋 Copy Questions", payload=reply),
            CopilotAction(action_type="shortlist", label=f"Shortlist {top_name}", application_id=top_candidate["application_id"], candidate_name=top_name),
        ]
    elif "email" in lower_query or "outreach" in lower_query or "invite" in lower_query:
        reply = (
            f"### Interview Invitation Draft: {top_name}\n\n"
            f"**Subject:** Invitation to Interview: {job_title} at TalentWright\n\n"
            f"Hi {top_name.split()[0]},\n\n"
            f"Thank you for applying for the **{job_title}** position. Our team has reviewed your background and was especially impressed by your experience with {', '.join(top_candidate.get('skills', [])[:3])} and your demonstrated project accomplishments.\n\n"
            f"We would love to schedule a 30-minute introductory conversation to discuss the role in more detail and learn more about your recent work.\n\n"
            f"Please let us know your availability over the next few days, or select a time directly via our calendar link.\n\n"
            f"Best regards,\nHiring Team"
        )
        actions = [
            CopilotAction(action_type="copy_text", label="📋 Copy Email Draft", payload=reply),
            CopilotAction(action_type="shortlist", label=f"Shortlist {top_name}", application_id=top_candidate["application_id"], candidate_name=top_name),
        ]
    else:
        top_3 = ", ".join(f"**{c['name']}** ({c['final_score']}%)" for c in candidates[:3])
        reply = (
            f"### Talent Pool Executive Summary for {job_title}\n\n"
            f"- **Total Candidates Evaluated:** {len(candidates)}\n"
            f"- **Top Tier Applicants:** {top_3}\n\n"
            f"**Key Findings:**\n"
            f"The candidate pool demonstrates strong technical capabilities. **{top_name}** leads the leaderboard with an overall match of **{top_score}%**, demonstrating exceptional alignment across experience and skills.\n\n"
            f"You can ask me to **compare specific candidates**, **generate tailored interview questions**, or **draft outreach emails**."
        )
        actions = [
            CopilotAction(action_type="shortlist", label=f"Shortlist {top_name}", application_id=top_candidate["application_id"], candidate_name=top_name),
        ]

    return CopilotResponse(reply=reply, suggested_actions=actions)


def execute_copilot_command(
    job: Job,
    message: str,
    history: list[CopilotMessage] | None = None,
    candidate_ids: list[int] | None = None,
) -> CopilotResponse:
    """Process recruiter command using LLM with context and structured action extraction."""
    context = build_recruiter_agent_context(job)
    system_prompt = _build_system_prompt(context)

    # Convert history into chat messages
    chat_history: list[dict[str, str]] = []
    if history:
        for msg in history[-6:]:  # Keep last 6 turns for context
            chat_history.append({"role": msg.role, "content": msg.content})

    chat_history.append({"role": "user", "content": message})

    try:
        provider = get_llm_provider()
        reply_text = provider.generate_chat_response(
            system_prompt=system_prompt,
            messages=chat_history,
            temperature=0.3,
        )

        actions = _detect_suggested_actions(reply_text, message, context["candidates"])
        return CopilotResponse(reply=reply_text, suggested_actions=actions)

    except (LLMProviderError, ValueError) as exc:
        logger.warning(
            "LLM call failed for copilot query on job %d (%s). Using fallback response.",
            job.id,
            exc,
        )
        return _generate_fallback_response(message, context)
    except Exception as exc:
        logger.exception("Unexpected error in copilot execution")
        return _generate_fallback_response(message, context)
