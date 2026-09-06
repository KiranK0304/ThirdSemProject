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
            "Search applicants for this job based on specific technical skills, domain "
            "experience, technologies, tools, or qualifications (e.g. 'PyTorch or deep learning', "
            "'Kubernetes in production', 'PostgreSQL performance tuning', 'payment gateways', 'AWS'). "
            "Returns relevant candidate profiles with specific resume evidence excerpts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The specific technical skill, domain experience, framework, or qualification to search for.",
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
