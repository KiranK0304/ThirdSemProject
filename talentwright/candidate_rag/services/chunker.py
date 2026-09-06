"""Semantic chunking service for structured resume data."""

from __future__ import annotations

from typing import Any

from talentwright.candidate_rag.models import ChunkType


def generate_resume_chunks(
    structured_resume: dict[str, Any],
    candidate_name: str = "",
) -> list[dict[str, Any]]:
    """Generate dense, semantic chunks from a structured resume dictionary.

    Args:
        structured_resume: Parsed structured resume dictionary.
        candidate_name: Full name of the candidate for embedding context.

    Returns:
        A list of dictionaries with keys:
            - 'chunk_type': ChunkType enum string
            - 'content': Full textual representation of the chunk
            - 'metadata': Contextual metadata dictionary
    """
    chunks: list[dict[str, Any]] = []
    name_header = candidate_name.strip() if candidate_name else "Candidate"

    # 1. Skills and Professional Summary Chunk
    summary = structured_resume.get("summary", "").strip()
    skills = structured_resume.get("skills", [])
    total_exp = structured_resume.get("total_years_experience", 0.0)

    if summary or skills:
        skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
        summary_lines = [
            f"Candidate: {name_header}",
            f"Total Professional Experience: {total_exp} years",
        ]
        if summary:
            summary_lines.extend(["Professional Summary:", summary])
        if skills_str:
            summary_lines.append(f"Core Technical Skills: {skills_str}")

        chunks.append(
            {
                "chunk_type": ChunkType.SKILLS_SUMMARY,
                "content": "\n".join(summary_lines),
                "metadata": {
                    "total_years_experience": float(total_exp) if total_exp else 0.0,
                    "skills": skills if isinstance(skills, list) else [],
                },
            }
        )

    # 2. Individual Work Experience Chunks
    work_experiences = structured_resume.get("work_experience", [])
    if isinstance(work_experiences, list):
        for exp in work_experiences:
            if not isinstance(exp, dict):
                continue

            company = exp.get("company", "").strip()
            title = exp.get("title", "").strip()
            start_date = exp.get("start_date", "").strip()
            end_date = exp.get("end_date", "").strip()
            if not end_date and exp.get("is_current"):
                end_date = "Present"
            dates = f"({start_date} - {end_date})" if start_date or end_date else ""

            technologies = exp.get("technologies", [])
            tech_str = ", ".join(technologies) if isinstance(technologies, list) else ""
            desc = exp.get("description", "").strip()

            exp_lines = [
                f"Candidate: {name_header}",
                f"Work Experience: {title} at {company} {dates}".strip(),
            ]
            if tech_str:
                exp_lines.append(f"Technologies Used: {tech_str}")
            if desc:
                exp_lines.extend(["Responsibilities & Achievements:", desc])

            chunks.append(
                {
                    "chunk_type": ChunkType.WORK_EXPERIENCE,
                    "content": "\n".join(exp_lines),
                    "metadata": {
                        "company": company,
                        "title": title,
                        "technologies": technologies if isinstance(technologies, list) else [],
                        "is_current": bool(exp.get("is_current")),
                    },
                }
            )

    # 3. Individual Project Chunks
    projects = structured_resume.get("projects", [])
    if isinstance(projects, list):
        for proj in projects:
            if not isinstance(proj, dict):
                continue

            title = proj.get("title", "").strip()
            technologies = proj.get("technologies", [])
            tech_str = ", ".join(technologies) if isinstance(technologies, list) else ""
            desc = proj.get("description", "").strip()

            proj_lines = [
                f"Candidate: {name_header}",
                f"Project: {title}",
            ]
            if tech_str:
                proj_lines.append(f"Technologies: {tech_str}")
            if desc:
                proj_lines.extend(["Project Description:", desc])

            chunks.append(
                {
                    "chunk_type": ChunkType.PROJECT,
                    "content": "\n".join(proj_lines),
                    "metadata": {
                        "title": title,
                        "technologies": technologies if isinstance(technologies, list) else [],
                    },
                }
            )

    # 4. Education and Certifications Chunk
    education_items = structured_resume.get("education", [])
    cert_items = structured_resume.get("certifications", [])

    if education_items or cert_items:
        edu_cert_lines = [f"Candidate: {name_header}"]

        if isinstance(education_items, list) and education_items:
            edu_cert_lines.append("Education:")
            for edu in education_items:
                if isinstance(edu, dict):
                    deg = edu.get("degree", "").strip()
                    field = edu.get("field_of_study", "").strip()
                    inst = edu.get("institution", "").strip()
                    yr = edu.get("graduation_year", "").strip()
                    qual = f"{deg} in {field}".strip(" in") if deg or field else "Degree"
                    where = f"from {inst}".strip() if inst else ""
                    when = f"({yr})" if yr else ""
                    edu_cert_lines.append(f"- {qual} {where} {when}".strip())

        if isinstance(cert_items, list) and cert_items:
            edu_cert_lines.append("Certifications:")
            for cert in cert_items:
                if isinstance(cert, dict):
                    c_name = cert.get("name", "").strip()
                    issuer = cert.get("issuer", "").strip()
                    issue_str = f"by {issuer}" if issuer else ""
                    edu_cert_lines.append(f"- {c_name} {issue_str}".strip())

        chunks.append(
            {
                "chunk_type": ChunkType.EDUCATION_CERTIFICATIONS,
                "content": "\n".join(edu_cert_lines),
                "metadata": {
                    "education_count": len(education_items) if isinstance(education_items, list) else 0,
                    "certifications_count": len(cert_items) if isinstance(cert_items, list) else 0,
                },
            }
        )

    return chunks
