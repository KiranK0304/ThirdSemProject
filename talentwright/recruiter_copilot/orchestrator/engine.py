"""Orchestrator engine coordinating conversation context, two-agent prompts, and tool execution."""

from __future__ import annotations

import json
import logging
from typing import Any

from talentwright.recruiter_copilot.models import CopilotMessage
from talentwright.recruiter_copilot.models import CopilotSession
from talentwright.recruiter_copilot.models import MessageRole
from talentwright.recruiter_copilot.prompts.copilot import build_orchestrator_prompt
from talentwright.recruiter_copilot.prompts.copilot import build_synthesis_prompt
from talentwright.recruiter_copilot.prompts.copilot import build_system_prompt
from talentwright.recruiter_copilot.tools.registry import ToolRegistry
from talentwright.recruiter_copilot.tools.registry import get_default_registry
from talentwright.resume_analysis.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class CopilotOrchestrator:
    """Orchestrates recruiter conversations using a clean two-agent workflow.

    Agent 1 (Tool Decision Agent):
      - Receives the tool orchestrator system prompt, chat history, and recruiter message.
      - Decides whether external tools are needed and outputs tool calls.

    Execution Layer:
      - Executes the decided tools against PostgreSQL and vector storage.

    Agent 2 (Response Synthesis Agent):
      - Receives a dedicated hiring advisor prompt, the shared chat history, and the retrieved candidate data.
      - Synthesizes an executive, evidence-grounded recommendation without tool artifacts.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.registry = registry or get_default_registry()

    def _get_conversation_history(
        self,
        session: CopilotSession,
        max_history: int = 10,
        exclude_message_id: int | None = None,
    ) -> list[dict[str, str]]:
        """Fetch recent message history between the recruiter and assistant."""
        qs = session.messages.all()
        if exclude_message_id is not None:
            qs = qs.exclude(id=exclude_message_id)
        history_records = list(qs.order_by("-created_at")[:max_history])
        history_records.reverse()

        messages: list[dict[str, str]] = []
        for msg in history_records:
            role_str = "user" if msg.role == MessageRole.USER else "assistant"
            messages.append({"role": role_str, "content": msg.content})
        return messages

    def _build_conversation_messages(
        self,
        session: CopilotSession,
        new_user_message: str,
        max_history: int = 10,
    ) -> list[dict[str, Any]]:
        """Build initial orchestrator messages array (kept for backwards compatibility)."""
        history = self._get_conversation_history(session, max_history=max_history)
        return [
            {"role": "system", "content": build_orchestrator_prompt(session.job)},
            *history,
            {"role": "user", "content": new_user_message},
        ]

    def _run_orchestrator_agent(
        self,
        session: CopilotSession,
        history: list[dict[str, str]],
        new_user_message: str,
    ) -> tuple[str | None, list[Any]]:
        """Step 1: Agent 1 analyzes the request and decides which tools to invoke.

        Returns:
            A tuple of (direct_reply_text, tool_calls_list).
        """
        tools = self.registry.get_definitions()
        messages = [
            {"role": "system", "content": build_orchestrator_prompt(session.job)},
            *history,
            {"role": "user", "content": new_user_message},
        ]

        response = self.llm_client.client.chat.completions.create(
            model=self.llm_client.model,
            messages=messages,
            tools=tools if tools else None,
            temperature=0.2,
        )

        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None) or []
        direct_reply = message.content or None
        return direct_reply, tool_calls

    def _execute_tools(
        self,
        tool_calls: list[Any],
        job_id: int,
    ) -> tuple[list[dict[str, Any]], Any]:
        """Step 2: Server-side execution of all tools selected by Agent 1.

        Returns:
            A tuple of (tools_called_metadata, all_tool_outputs).
            When a single tool is called, returns its output directly for
            backwards compatibility.  When multiple tools are called, returns
            a dict keyed by tool name.
        """
        tools_called_meta: list[dict[str, Any]] = []
        all_outputs: dict[str, Any] = {}

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args_str = tool_call.function.arguments or "{}"
            try:
                tool_args = json.loads(tool_args_str)
            except json.JSONDecodeError:
                tool_args = {}

            tools_called_meta.append({"name": tool_name, "arguments": tool_args})

            # Execute tool with secure job context
            tool_output = self.registry.execute(
                tool_name=tool_name,
                arguments=tool_args,
                context={"job_id": job_id},
            )
            all_outputs[tool_name] = tool_output

        # Single tool: return its output directly for backwards compatibility
        if len(all_outputs) == 1:
            return tools_called_meta, next(iter(all_outputs.values()))

        return tools_called_meta, all_outputs

    def _run_synthesis_agent(
        self,
        session: CopilotSession,
        history: list[dict[str, str]],
        new_user_message: str,
        candidate_data: Any,
    ) -> str:
        """Step 3: Agent 2 receives candidate data and generates the final advisory response."""
        synthesis_messages: list[dict[str, Any]] = [
            {"role": "system", "content": build_synthesis_prompt(session.job)},
            *history,
        ]

        # Structure candidate data into the prompt cleanly
        synthesis_prompt = (
            f"Recruiter Inquiry:\n\"{new_user_message}\"\n\n"
            f"Candidate Data Retrieved from Database for this Job:\n"
            f"{json.dumps(candidate_data, separators=(',', ':'))}\n\n"
            f"Please evaluate these candidates and deliver your executive hiring response."
        )
        synthesis_messages.append({"role": "user", "content": synthesis_prompt})

        response = self.llm_client.client.chat.completions.create(
            model=self.llm_client.model,
            messages=synthesis_messages,
            temperature=0.3,
        )
        return response.choices[0].message.content or ""

    def run(
        self,
        session: CopilotSession,
        new_user_message: str,
        exclude_message_id: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Execute one conversational turn through the two-agent architecture.

        Args:
            session: The active CopilotSession.
            new_user_message: The text input from the recruiter.
            exclude_message_id: Optional ID of the just-saved user message to
                exclude from conversation history (prevents duplicate inclusion
                since new_user_message is appended separately).

        Returns:
            A tuple of (assistant_reply_text, metadata_dict).
        """
        metadata: dict[str, Any] = {"tools_called": []}

        try:
            # 1. Retrieve shared conversation history
            history = self._get_conversation_history(
                session, exclude_message_id=exclude_message_id,
            )

            # 2. Agent 1: Tool Decision Agent
            direct_reply, tool_calls = self._run_orchestrator_agent(
                session=session,
                history=history,
                new_user_message=new_user_message,
            )

            # If no tools are required, return direct conversational answer
            if not tool_calls:
                return direct_reply or "", metadata

            # 3. Execution Layer: Execute tools selected by Agent 1
            tools_called, candidate_data = self._execute_tools(
                tool_calls=tool_calls,
                job_id=session.job_id,
            )
            metadata["tools_called"] = tools_called
            metadata["candidates"] = candidate_data

            # 4. Agent 2: Final Response Synthesis Agent
            assistant_text = self._run_synthesis_agent(
                session=session,
                history=history,
                new_user_message=new_user_message,
                candidate_data=candidate_data,
            )
            return assistant_text, metadata

        except Exception as exc:
            logger.exception("Error in CopilotOrchestrator: %s", exc)
            fallback_text = (
                "I apologize, but I encountered an issue while processing your request. "
                "Please try again or rephrase your question."
            )
            return fallback_text, {"error": str(exc)}
