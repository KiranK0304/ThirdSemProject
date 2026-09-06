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
