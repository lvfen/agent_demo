from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

Audience = Literal["customer", "agent", "both"]
MessageRole = Literal["user", "assistant", "agent", "system"]
OwnerState = Literal["ai_active", "human_active", "ai_paused"]
AgentStatus = Literal["normal", "needs_followup", "escalated_backoffice", "waiting_human"]


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Message(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("msg"))
    role: MessageRole
    text: str
    audience: Audience = "both"
    visible_in_transcript: bool = True
    created_at: str = Field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def user(cls, text: str, audience: Audience = "both") -> "Message":
        return cls(role="user", text=text, audience=audience)

    @classmethod
    def assistant(cls, text: str, audience: Audience = "both", metadata: dict[str, Any] | None = None) -> "Message":
        return cls(role="assistant", text=text, audience=audience, metadata=metadata or {})

    @classmethod
    def agent(cls, text: str, audience: Audience = "both", metadata: dict[str, Any] | None = None) -> "Message":
        return cls(role="agent", text=text, audience=audience, metadata=metadata or {})


class Event(BaseModel):
    type: str
    audience: Audience
    created_at: str = Field(default_factory=utc_now_iso)
    payload: dict[str, Any]


class SessionState(BaseModel):
    session_id: str = "default"
    messages: list[Message] = Field(default_factory=list)
    owner: OwnerState = "ai_active"
    agent_status: AgentStatus = "normal"
    handoff_reason: str | None = None
    conversation_summary: str = ""
    ai_reply_task: Any = None
    ai_typing: bool = False
    last_error: str | None = None

