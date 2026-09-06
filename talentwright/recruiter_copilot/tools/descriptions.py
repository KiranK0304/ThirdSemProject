"""OpenAI-compatible tool definitions and schema descriptions for recruiter copilot."""

from __future__ import annotations

RANKED_CANDIDATES_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_ranked_candidates",
        "description": (
            "Retrieve applicants for this job ordered by their objective resume compatibility score. "
            "Use this when the recruiter asks for the best/top candidates, who to interview first, "
            "ranking, or who are the weakest/lowest scoring applicants."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of candidates to retrieve (default is 5, max is 20).",
                    "default": 5,
                },
                "ranking": {
                    "type": "string",
                    "enum": ["highest_score", "lowest_score"],
                    "description": (
                        "Ranking direction: 'highest_score' for top/best candidates, "
                        "or 'lowest_score' for weakest/lowest scoring candidates."
                    ),
                    "default": "highest_score",
                },
            },
            "required": [],
        },
    },
}

# Alias for backwards compatibility if referenced by legacy handlers
TOP_CANDIDATES_TOOL_DEFINITION = RANKED_CANDIDATES_TOOL_DEFINITION
