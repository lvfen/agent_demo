from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from app.config import Settings
from app.models import FollowupDecision, Message
from app.prompting import build_support_messages

Responder = Callable[[list[dict[str, str]]], Awaitable[str]]


class SupportAgentService:
    def __init__(
        self,
        settings: Settings | None = None,
        fake_response: str | None = None,
        responder: Responder | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.fake_response = fake_response
        self.responder = responder

    async def generate_reply(
        self,
        messages: list[Message],
        summary: str,
        agent_status: str,
    ) -> Message:
        prompt_messages = build_support_messages(messages, summary, agent_status)
        text = self.fake_response or await self._call_model(prompt_messages)
        return Message.assistant(text=text, audience="both")

    async def evaluate_request(self, text: str) -> FollowupDecision:
        lowered = text.lower()
        restricted_tokens = ("refund", "bank card", "compensation", "payout", "account info")
        if any(token in lowered for token in restricted_tokens):
            return FollowupDecision(
                requires_followup=True,
                agent_status="needs_followup",
                holding_message="I am checking this for you now. Give me a moment.",
            )
        return FollowupDecision(requires_followup=False, agent_status="normal")

    async def _call_model(self, prompt_messages: list[dict[str, str]]) -> str:
        if self.responder is not None:
            return await self.responder(prompt_messages)

        try:
            return await asyncio.wait_for(self._call_deep_agent(prompt_messages), timeout=20)
        except Exception:
            return "I am checking this for you now. Give me a moment."

    async def _call_deep_agent(self, prompt_messages: list[dict[str, str]]) -> str:
        try:
            from deepagents import create_deep_agent  # type: ignore
            from litellm import acompletion  # type: ignore
        except Exception:
            return "I am checking this for you now. Give me a moment."

        async def model_call(messages: list[dict[str, Any]]) -> str:
            response = await acompletion(
                model=self.settings.litellm_model,
                messages=messages,
                api_key=self.settings.litellm_api_key,
                base_url=self.settings.litellm_base_url,
            )
            return response["choices"][0]["message"]["content"]

        agent = create_deep_agent(model=model_call)
        result = await agent.ainvoke({"messages": prompt_messages})
        if isinstance(result, dict):
            if "output" in result and isinstance(result["output"], str):
                return result["output"]
            if "messages" in result and result["messages"]:
                last_message = result["messages"][-1]
                if isinstance(last_message, dict):
                    return str(last_message.get("content", "I am checking this for you now."))
                content = getattr(last_message, "content", None)
                if isinstance(content, str):
                    return content
        return "I am checking this for you now. Give me a moment."
