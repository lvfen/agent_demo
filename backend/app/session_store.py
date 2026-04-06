from __future__ import annotations

from app.models import Message, SessionState


class SessionStore:
    def __init__(self) -> None:
        self._session = SessionState()

    def get_session(self) -> SessionState:
        return self._session

    def build_snapshot(self, audience: str) -> dict:
        base = {
            "session_id": self._session.session_id,
            "messages": [message.model_dump() for message in self._visible_messages(audience)],
            "owner": self._session.owner,
            "ai_typing": self._session.ai_typing,
        }
        if audience == "agent":
            base["agent_status"] = self._session.agent_status
            base["last_error"] = self._session.last_error
        return base

    def append_message(self, message: Message) -> Message:
        self._session.messages.append(message)
        self._update_summary(message)
        return message

    def mark_followup(self, reason: str, status: str = "needs_followup") -> None:
        self._session.owner = "ai_paused"
        self._session.agent_status = status
        self._session.handoff_reason = reason

    def takeover(self, reason: str = "manual_takeover") -> None:
        self._session.owner = "human_active"
        self._session.handoff_reason = reason
        self._session.agent_status = "waiting_human"

    def release_to_ai(self) -> None:
        self._session.owner = "ai_active"
        self._session.agent_status = "normal"
        self._session.handoff_reason = None

    def resume_ai(self) -> None:
        self._session.owner = "ai_active"
        self._session.agent_status = "normal"

    def set_ai_typing(self, active: bool) -> None:
        self._session.ai_typing = active

    def set_last_error(self, error: str | None) -> None:
        self._session.last_error = error

    def _visible_messages(self, audience: str) -> list[Message]:
        return [message for message in self._session.messages if message.audience in {audience, "both"}]

    def _update_summary(self, message: Message) -> None:
        if message.role == "user":
            self._session.conversation_summary = f"Latest customer issue: {message.text}"
        elif message.role in {"assistant", "agent"}:
            self._session.conversation_summary = f"{self._session.conversation_summary} | Last support action: {message.text}".strip(" |")
