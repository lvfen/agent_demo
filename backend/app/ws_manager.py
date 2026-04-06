from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.agent_service import SupportAgentService
from app.models import Event, Message
from app.session_store import SessionStore


class WebSocketManager:
    def __init__(self, store: SessionStore, agent_service: SupportAgentService) -> None:
        self.store = store
        self.agent_service = agent_service
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, audience: str) -> None:
        await websocket.accept()
        self.connections[audience].add(websocket)
        await websocket.send_json(self._session_snapshot_event(audience).model_dump())

    def disconnect(self, websocket: WebSocket, audience: str) -> None:
        self.connections[audience].discard(websocket)

    async def handle_customer_loop(self, websocket: WebSocket) -> None:
        try:
            while True:
                event = await websocket.receive_json()
                if event.get("type") == "user_message":
                    await self._handle_customer_message(event["payload"]["text"])
        except WebSocketDisconnect:
            self.disconnect(websocket, "customer")

    async def handle_agent_loop(self, websocket: WebSocket) -> None:
        try:
            while True:
                event = await websocket.receive_json()
                event_type = event.get("type")
                if event_type == "takeover":
                    self.store.takeover(reason=event.get("payload", {}).get("reason", "manual_takeover"))
                    await self.broadcast_event(
                        Event(
                            type="ownership_changed",
                            audience="both",
                            payload={"owner": self.store.get_session().owner, "reason": self.store.get_session().handoff_reason},
                        )
                    )
                elif event_type == "release_to_ai":
                    self.store.release_to_ai()
                    await self.broadcast_event(
                        Event(
                            type="ownership_changed",
                            audience="both",
                            payload={"owner": self.store.get_session().owner, "reason": "release_to_ai"},
                        )
                    )
                elif event_type == "resume_ai":
                    self.store.resume_ai()
                    await self.broadcast_event(
                        Event(
                            type="ownership_changed",
                            audience="both",
                            payload={"owner": self.store.get_session().owner, "reason": "resume_ai"},
                        )
                    )
                elif event_type == "agent_message":
                    if self.store.get_session().owner != "human_active":
                        await self.broadcast_event(
                            Event(
                                type="error_notice",
                                audience="agent",
                                payload={
                                    "code": "AGENT_MESSAGE_REJECTED",
                                    "message": "Take over the conversation before sending a human reply",
                                },
                            )
                        )
                        continue
                    message = self.store.append_message(Message.agent(text=event["payload"]["text"], audience="both"))
                    await self.broadcast_event(Event(type="message_created", audience="both", payload=message.model_dump()))
        except WebSocketDisconnect:
            self.disconnect(websocket, "agent")

    async def _handle_customer_message(self, text: str) -> None:
        message = self.store.append_message(Message.user(text=text, audience="both"))
        await self.broadcast_event(Event(type="message_created", audience="both", payload=message.model_dump()))

        session = self.store.get_session()
        if session.owner == "human_active":
            return

        decision = await self.agent_service.evaluate_request(text)
        if decision.requires_followup:
            self.store.mark_followup(reason="restricted_request", status=decision.agent_status)
            holding_text = decision.holding_message or "I am checking this for you now. Give me a moment."
            holding_message = self.store.append_message(Message.assistant(text=holding_text, audience="both"))
            await self.broadcast_event(Event(type="message_created", audience="both", payload=holding_message.model_dump()))
            await self.broadcast_event(
                Event(
                    type="system_notice",
                    audience="agent",
                    payload={"code": "FOLLOWUP_REQUIRED", "message": "Case marked for internal follow-up"},
                )
            )
            return

        if session.owner == "ai_paused":
            return

        self.store.set_ai_typing(True)
        await self.broadcast_event(Event(type="ai_typing", audience="both", payload={"active": True}))
        reply = await self.agent_service.generate_reply(
            messages=self.store.get_session().messages,
            summary=self.store.get_session().conversation_summary,
            agent_status=self.store.get_session().agent_status,
        )
        if self.store.get_session().owner == "ai_active":
            saved_reply = self.store.append_message(reply)
            await self.broadcast_event(Event(type="message_created", audience="both", payload=saved_reply.model_dump()))
        self.store.set_ai_typing(False)
        await self.broadcast_event(Event(type="ai_typing", audience="both", payload={"active": False}))

    async def broadcast_event(self, event: Event) -> None:
        recipients: set[WebSocket] = set()
        if event.audience in {"customer", "both"}:
            recipients.update(self.connections["customer"])
        if event.audience in {"agent", "both"}:
            recipients.update(self.connections["agent"])

        for websocket in list(recipients):
            await websocket.send_json(event.model_dump())

    def _session_snapshot_event(self, audience: str) -> Event:
        return Event(
            type="session_snapshot",
            audience=audience,
            payload=self.store.build_snapshot(audience=audience),
        )
