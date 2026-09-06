"""OpenAI-compatible tool definitions and schema descriptions for recruiter copilot."""

from __future__ import annotations

TOP_CANDIDATES_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_top_candidates",
        "description": (
            "Retrieve top-ranked applicants for this job ordered by their objective "
            "resume compatibility score. Use this when the recruiter asks for the best candidates, "
            "top applicants, or who to interview first."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of candidates to retrieve (default is 5, max is 20).",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
}

SEARCH_CANDIDATES_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "search_candidates",
        "description": (
            "Search applicants for this job using semantic retrieval over their resumes. "
            "Use this for specific technical skills, tools, frameworks, domain backgrounds, "
            "as well as career stages or role titles (e.g. 'PyTorch or deep learning', "
            "'junior or early career developer', 'startup backend engineer', "
            "'PostgreSQL performance tuning', 'AWS infrastructure'). "
            "Translates recruiter criteria into semantic resume concepts to return matching profiles "
            "with verified evidence excerpts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The semantic search query: technical skills, frameworks, domain experience, or career stage / role seniority.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of candidate matches to return (default: 5, max: 10).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}
