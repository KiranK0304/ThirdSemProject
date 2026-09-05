"""Tool registry for the Recruiter Copilot AI agent."""

from __future__ import annotations

import logging
from typing import Any, Callable

from talentwright.recruiter_copilot.tools.candidates import get_top_candidates

logger = logging.getLogger(__name__)

# Standard OpenAI-compatible tool definitions
TOP_CANDIDATES_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_top_candidates",
        "description": (
            "Retrieve the top-ranked candidates who applied for this job, "
            "ordered by their objective resume compatibility score. "
            "Call this tool when the recruiter asks for the best candidates, "
            "top applicants, who to interview first, or candidate ranking."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of top candidates to retrieve (default is 5, max is 20).",
                    "default": 5,
                },
            },
            "required": [],
        },
    },
}


class ToolRegistry:
    """Registry holding all capabilities the copilot can execute."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}
        self._definitions: list[dict[str, Any]] = []

    def register(
        self,
        name: str,
        definition: dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        """Register a new tool and its executable handler."""
        self._tools[name] = handler
        self._definitions.append(definition)

    def get_definitions(self) -> list[dict[str, Any]]:
        """Return tool definitions formatted for OpenRouter / OpenAI API."""
        return list(self._definitions)

    def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> Any:
        """Execute a registered tool by name with arguments and secure context.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Arguments parsed from the LLM tool call.
            context: Injected server-side context (e.g. verified job_id).

        Returns:
            The output of the tool execution.

        Raises:
            ValueError: If tool_name is not registered.
        """
        handler = self._tools.get(tool_name)
        if not handler:
            msg = f"Tool '{tool_name}' is not registered in the copilot registry."
            raise ValueError(msg)

        # Merge arguments with server context (e.g. job_id)
        call_kwargs = {**arguments, **context}
        logger.info("Executing tool '%s' with kwargs: %s", tool_name, call_kwargs)
        return handler(**call_kwargs)


def get_default_registry() -> ToolRegistry:
    """Build and return the default ToolRegistry with built-in tools."""
    registry = ToolRegistry()

    # Register 1: get_top_candidates
    registry.register(
        name="get_top_candidates",
        definition=TOP_CANDIDATES_TOOL_DEFINITION,
        handler=get_top_candidates,
    )

    return registry
