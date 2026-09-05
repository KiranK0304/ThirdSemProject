"""Orchestrator engine coordinating conversation context, LLM, and tool calling."""

from __future__ import annotations

import json
import logging
from typing import Any

from talentwright.recruiter_copilot.models import CopilotMessage
from talentwright.recruiter_copilot.models import CopilotSession
from talentwright.recruiter_copilot.models import MessageRole
from talentwright.recruiter_copilot.prompts.copilot import build_system_prompt
from talentwright.recruiter_copilot.tools.registry import ToolRegistry
from talentwright.recruiter_copilot.tools.registry import get_default_registry
from talentwright.resume_analysis.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class CopilotOrchestrator:
    """Orchestrates multi-turn recruiter conversations with tool calling."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.registry = registry or get_default_registry()

    def _build_conversation_messages(
        self,
        session: CopilotSession,
        new_user_message: str,
        max_history: int = 10,
    ) -> list[dict[str, Any]]:
        """Construct conversation message payload including system prompt and recent history."""
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_system_prompt(session.job)}
        ]

        # Fetch recent session history (excluding the new message that was just created)
        history_records = list(session.messages.order_by("-created_at")[:max_history])
        history_records.reverse()

        for msg in history_records:
            # Map database MessageRole to OpenAI roles
            role_str = "user" if msg.role == MessageRole.USER else "assistant"
            messages.append({"role": role_str, "content": msg.content})

        # Append current user prompt
        messages.append({"role": "user", "content": new_user_message})
        return messages

    def run(
        self,
        session: CopilotSession,
        new_user_message: str,
    ) -> tuple[str, dict[str, Any]]:
        """Execute one conversational turn with the copilot.

        Args:
            session: The active CopilotSession.
            new_user_message: The text input from the recruiter.

        Returns:
            A tuple of (assistant_reply_text, metadata_dict).
        """
        messages = self._build_conversation_messages(session, new_user_message)
        tools = self.registry.get_definitions()
        metadata: dict[str, Any] = {"tools_called": []}

        try:
            # Step 1: Initial call to LLM with tools
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=messages,
                tools=tools if tools else None,
                temperature=0.2,
            )

            choice = response.choices[0]
            message = choice.message

            # Step 2: Check if LLM decided to call a tool
            if getattr(message, "tool_calls", None):
                # Append assistant's tool_calls message
                messages.append(message)

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments or "{}"
                    try:
                        tool_args = json.loads(tool_args_str)
                    except json.JSONDecodeError:
                        tool_args = {}

                    metadata["tools_called"].append(
                        {"name": tool_name, "arguments": tool_args}
                    )

                    # Execute the tool via our registry
                    tool_output = self.registry.execute(
                        tool_name=tool_name,
                        arguments=tool_args,
                        context={"job_id": session.job_id},
                    )

                    # Attach candidate list directly to metadata for frontend rendering
                    if tool_name == "get_top_candidates":
                        metadata["candidates"] = tool_output

                    # Append tool result to messages for the LLM
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_output),
                        }
                    )

                # Step 3: Second call to LLM with the tool output so it generates conversational response
                second_response = self.llm_client.client.chat.completions.create(
                    model=self.llm_client.model,
                    messages=messages,
                    temperature=0.2,
                )
                assistant_text = second_response.choices[0].message.content or ""
                return assistant_text, metadata

            # If no tool was called, return the direct conversational reply
            assistant_text = message.content or ""
            return assistant_text, metadata

        except Exception as exc:
            logger.exception("Error in CopilotOrchestrator: %s", exc)
            fallback_text = (
                "I apologize, but I encountered an issue while processing your request. "
                "Please try again or rephrase your question."
            )
            return fallback_text, {"error": str(exc)}
