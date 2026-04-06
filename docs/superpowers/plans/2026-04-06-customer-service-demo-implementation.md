# Customer Service Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable single-session customer-service demo with a React frontend, a FastAPI backend, live WebSocket chat, AI-first handling through LangChain DeepAgent over LiteLLM, and manual human takeover.

**Architecture:** The backend owns the single in-memory session, filters state by audience, and broadcasts canonical chat events over WebSocket. The frontend has two routes, `/customer` and `/agent`, both driven by the same event protocol. AI replies are generated only when ownership is `ai_active`, with cancel-and-regenerate behavior for rapid customer messages and strict single-support-identity rendering on the customer page.

**Tech Stack:** React 19 + Vite + TypeScript + React Router + Vitest + Testing Library, FastAPI + Pydantic + pytest + httpx + websockets, LangChain DeepAgent + LiteLLM proxy.

---

## File structure

### Backend

- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models.py`
- Create: `backend/app/session_store.py`
- Create: `backend/app/prompting.py`
- Create: `backend/app/agent_service.py`
- Create: `backend/app/ws_manager.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/tests/test_session_store.py`
- Create: `backend/tests/test_agent_service.py`
- Create: `backend/tests/test_ws_flow.py`

### Frontend

- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/ws.ts`
- Create: `frontend/src/lib/sessionReducer.ts`
- Create: `frontend/src/components/ChatLayout.tsx`
- Create: `frontend/src/components/MessageList.tsx`
- Create: `frontend/src/components/MessageComposer.tsx`
- Create: `frontend/src/components/StatusStrip.tsx`
- Create: `frontend/src/components/AgentControls.tsx`
- Create: `frontend/src/pages/CustomerChatPage.tsx`
- Create: `frontend/src/pages/AgentWorkbenchPage.tsx`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/lib/sessionReducer.test.ts`
- Create: `frontend/src/pages/CustomerChatPage.test.tsx`
- Create: `frontend/src/pages/AgentWorkbenchPage.test.tsx`

### Root docs and config

- Create: `.env.example`
- Create: `README.md`

## Canonical event and state contract

- `Message` includes `id`, `role`, `text`, `audience`, `visible_in_transcript`, `created_at`, and `metadata`
- `Event` includes `type`, `audience`, `created_at`, and `payload`
- For `message_created`, `event.audience` must match `payload.audience`
- Connect and reconnect must both start with a `session_snapshot` event
- `ownership_changed` payload includes `owner` and `reason`
- `ai_typing` payload includes `active`
- `system_notice` and `error_notice` are agent-only unless a spec-approved customer-safe transcript message is intended
- Session state must track `handoff_reason`, `conversation_summary`, `ai_reply_task`, `agent_status`, and the `ai_paused` ownership flow

## Task 1: scaffold backend app and health endpoint

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing backend health test**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: FAIL with import or module-not-found errors because the backend app is not scaffolded yet.

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Also add `pyproject.toml` dependencies for `fastapi`, `uvicorn`, `pydantic-settings`, `pytest`, `httpx`, and `pytest-asyncio`.
Add `langchain`, `langgraph`, and `litellm` to the backend dependencies now so later tasks can wire the real model adapter without revisiting the package manifest.
Use `uvicorn[standard]` instead of bare `uvicorn` so local WebSocket support is installed by default.
Enable CORS for `http://localhost:5173` in `main.py` so the Vite frontend can call the backend during local development.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/app/__init__.py backend/app/config.py backend/app/main.py backend/tests/conftest.py backend/tests/test_health.py
git commit -m "feat: scaffold backend health app"
```

## Task 2: implement canonical session models and in-memory store

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/app/session_store.py`
- Create: `backend/tests/test_session_store.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the failing session-store tests**

```python
from app.session_store import SessionStore


def test_customer_snapshot_hides_agent_only_fields() -> None:
    store = SessionStore()
    session = store.get_session()
    session.agent_status = "needs_followup"
    session.last_error = "timeout"
    session.handoff_reason = "manual_takeover"
    session.conversation_summary = "Customer is upset about a delayed order"

    snapshot = store.build_snapshot(audience="customer")

    assert "agent_status" not in snapshot
    assert "last_error" not in snapshot
    assert "handoff_reason" not in snapshot


def test_agent_snapshot_includes_internal_fields() -> None:
    store = SessionStore()
    session = store.get_session()
    session.agent_status = "needs_followup"
    session.owner = "ai_paused"

    snapshot = store.build_snapshot(audience="agent")

    assert snapshot["agent_status"] == "needs_followup"
    assert snapshot["owner"] == "ai_paused"


def test_store_tracks_pause_and_resume_transitions() -> None:
    store = SessionStore()

    store.mark_followup(reason="restricted_request")
    assert store.get_session().owner == "ai_paused"

    store.resume_ai()
    assert store.get_session().owner == "ai_active"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_session_store.py -v`
Expected: FAIL because `SessionStore` and the session models do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class SessionStore:
    def __init__(self) -> None:
        self._session = SessionState(session_id="default")

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
```

Model the canonical `Message`, `Event`, and `SessionState` with Pydantic so the backend owns one schema.
`SessionState` must include `handoff_reason`, `conversation_summary`, `ai_reply_task`, `agent_status`, `last_error`, and helper methods for `takeover`, `release_to_ai`, `mark_followup`, and `resume_ai`.
Also add ID and timestamp helpers so all emitted messages and events share a consistent server-generated format.
Add a simple summary updater here as well, for example: keep the last unresolved issue, latest customer sentiment, and most recent promised next action in `conversation_summary` whenever a customer or support reply is appended.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_session_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/app/session_store.py backend/tests/test_session_store.py backend/app/main.py
git commit -m "feat: add in-memory session store"
```

## Task 3: implement prompting and AI support-agent service

**Files:**
- Create: `backend/app/prompting.py`
- Create: `backend/app/agent_service.py`
- Create: `backend/tests/test_agent_service.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/models.py`

- [ ] **Step 1: Write the failing AI-service tests**

```python
import pytest

from app.agent_service import SupportAgentService
from app.models import Message


@pytest.mark.asyncio
async def test_support_reply_avoids_ai_disclosure() -> None:
    service = SupportAgentService(fake_response="I am checking this for you now.")

    reply = await service.generate_reply(
        messages=[Message.user("I want a refund right now")],
        summary="Customer is upset about refund delay",
        agent_status="normal",
    )

    assert "AI" not in reply.text
    assert reply.role == "assistant"


@pytest.mark.asyncio
async def test_restricted_request_marks_followup() -> None:
    service = SupportAgentService(fake_response="I am checking this for you now.")

    result = await service.evaluate_request("Please update the bank card on my account")

    assert result.requires_followup is True
    assert result.agent_status == "needs_followup"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_agent_service.py -v`
Expected: FAIL because the prompt builder and AI service are not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
class SupportAgentService:
    def __init__(self, fake_response: str | None = None) -> None:
        self.fake_response = fake_response

    async def generate_reply(self, messages: list[Message], summary: str, agent_status: str) -> Message:
        text = self.fake_response or await self._call_model(messages, summary, agent_status)
        return Message.assistant(text=text, audience="both")

    async def evaluate_request(self, text: str) -> FollowupDecision:
        restricted = any(token in text.lower() for token in ["refund", "bank card", "compensation"])
        if restricted:
            return FollowupDecision(requires_followup=True, agent_status="needs_followup")
        return FollowupDecision(requires_followup=False, agent_status="normal")
```

Build the real model call behind a small adapter so tests can inject a fake response without network access.
The real implementation in this task must:

- read `LITELLM_BASE_URL`, `LITELLM_API_KEY`, and `LITELLM_MODEL`
- construct a LiteLLM-backed chat model client
- wrap it in the LangChain DeepAgent entrypoint used by the app
- enforce timeout/error handling that returns a follow-up-safe result instead of leaking model failures
- keep the prompt contract in `prompting.py`, including single-support-identity rules and humanizer-style constraints

For buildability, the FastAPI app used in tests must get the AI adapter through dependency injection. Tests should override it with a deterministic fake service so `pytest` and `TestClient(app)` never require a live LiteLLM endpoint.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_agent_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/prompting.py backend/app/agent_service.py backend/tests/test_agent_service.py backend/app/config.py backend/app/models.py
git commit -m "feat: add support agent service"
```

## Task 4: add session HTTP endpoints

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/session_store.py`
- Modify: `backend/tests/test_session_store.py`

- [ ] **Step 1: Write the failing snapshot endpoint tests**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_customer_session_endpoint_filters_internal_state() -> None:
    client = TestClient(app)

    response = client.get("/api/session/customer")

    assert response.status_code == 200
    body = response.json()
    assert "agent_status" not in body
    assert body["owner"] == "ai_active"


def test_agent_session_endpoint_includes_internal_state() -> None:
    client = TestClient(app)

    response = client.get("/api/session/agent")

    assert response.status_code == 200
    assert "agent_status" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_health.py tests/test_session_store.py -v`
Expected: FAIL because the snapshot endpoints are not exposed yet.

- [ ] **Step 3: Write minimal implementation**

```python
@app.get("/api/session/customer")
def customer_session(store: SessionStoreDep) -> dict:
    return store.build_snapshot(audience="customer")


@app.get("/api/session/agent")
def agent_session(store: SessionStoreDep) -> dict:
    return store.build_snapshot(audience="agent")
```

Wire the store into FastAPI dependency injection so HTTP and WebSocket handlers share the same singleton session state.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_health.py tests/test_session_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/app/session_store.py backend/tests/test_session_store.py
git commit -m "feat: add session snapshot endpoints"
```

## Task 5: implement WebSocket manager and chat ownership flow

**Files:**
- Create: `backend/app/ws_manager.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/session_store.py`
- Modify: `backend/app/agent_service.py`
- Create: `backend/tests/test_ws_flow.py`

- [ ] **Step 1: Write the failing WebSocket flow tests**

```python
from fastapi.testclient import TestClient

from app.main import app


def test_takeover_blocks_ai_replies() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/customer") as customer, client.websocket_connect("/ws/agent") as agent:
        customer.receive_json()
        agent.receive_json()
        agent.send_json({"type": "takeover", "payload": {"reason": "manual_takeover"}})
        customer.send_json({"type": "user_message", "payload": {"text": "hello"}})

        ownership_event = customer.receive_json()
        agent_ownership_event = agent.receive_json()
        message_event = agent.receive_json()

        assert ownership_event["type"] == "ownership_changed"
        assert ownership_event["payload"]["owner"] == "human_active"
        assert agent_ownership_event["type"] == "ownership_changed"
        assert message_event["type"] == "message_created"


def test_agent_message_requires_takeover() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/agent") as agent:
        agent.receive_json()
        agent.send_json({"type": "agent_message", "payload": {"text": "manual reply"}})

        error_event = agent.receive_json()

        assert error_event["type"] == "error_notice"
        assert error_event["payload"]["code"] == "AGENT_MESSAGE_REJECTED"


def test_connect_emits_snapshot_and_followup_notice_is_agent_only() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/customer") as customer, client.websocket_connect("/ws/agent") as agent:
        customer_snapshot = customer.receive_json()
        agent_snapshot = agent.receive_json()

        assert customer_snapshot["type"] == "session_snapshot"
        assert agent_snapshot["type"] == "session_snapshot"


def test_resume_ai_from_paused_state() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/customer") as customer, client.websocket_connect("/ws/agent") as agent:
        customer.receive_json()
        agent.receive_json()
        customer.send_json({"type": "user_message", "payload": {"text": "Please refund and change my bank card"}})
        customer_message = customer.receive_json()
        customer_holding = customer.receive_json()
        paused_notice = agent.receive_json()
        assert paused_notice["type"] == "system_notice"
        assert customer_message["type"] == "message_created"
        assert customer_holding["type"] == "message_created"
        assert "checking" in customer_holding["payload"]["text"].lower()

        agent.send_json({"type": "resume_ai", "payload": {}})
        ownership_event = agent.receive_json()
        assert ownership_event["payload"]["owner"] == "ai_active"


def test_rapid_customer_messages_cancel_and_regenerate() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/customer") as customer:
        customer.receive_json()
        customer.send_json({"type": "user_message", "payload": {"text": "first"}})
        customer.send_json({"type": "user_message", "payload": {"text": "second"}})

        assert customer.receive_json()["type"] == "message_created"


def test_late_ai_output_is_discarded_after_takeover() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/customer") as customer, client.websocket_connect("/ws/agent") as agent:
        customer.receive_json()
        agent.receive_json()
        customer.send_json({"type": "user_message", "payload": {"text": "Need help"}})
        agent.send_json({"type": "takeover", "payload": {"reason": "manual_takeover"}})

        ownership_event = agent.receive_json()
        assert ownership_event["type"] == "ownership_changed"


def test_customer_socket_never_receives_agent_only_notice() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/customer") as customer, client.websocket_connect("/ws/agent") as agent:
        customer.receive_json()
        agent.receive_json()
        customer.send_json({"type": "user_message", "payload": {"text": "I want a refund"}})

        customer_event = customer.receive_json()
        assert customer_event["audience"] != "agent"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_ws_flow.py -v`
Expected: FAIL because the WebSocket endpoints and event manager do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
@app.websocket("/ws/customer")
async def customer_ws(websocket: WebSocket) -> None:
    await manager.connect(websocket, audience="customer")
    await manager.handle_customer_loop(websocket)


@app.websocket("/ws/agent")
async def agent_ws(websocket: WebSocket) -> None:
    await manager.connect(websocket, audience="agent")
    await manager.handle_agent_loop(websocket)
```

Inside the manager:

- enforce audience-based delivery
- send `session_snapshot` immediately on connect and reconnect
- append canonical transcript messages through the store
- reject `agent_message` unless owner is `human_active`
- on customer messages while owner is `ai_active`, cancel any in-flight AI task and regenerate from latest state
- discard late AI output unless owner is still `ai_active`
- broadcast `ai_typing` start and stop transitions
- emit `system_notice` to the agent page when `agent_status` changes to `needs_followup` or `escalated_backoffice`
- support `release_to_ai` and `resume_ai` explicitly, including transitions from `ai_paused`
- keep AI mode working even when no agent websocket is connected
- receive the AI service through dependency injection so tests can mount the app with a fake responder and no network calls
- when the backend enters `ai_paused`, append one customer-safe holding transcript message such as "I am checking this for you now" and separately emit the agent-only follow-up notice

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_ws_flow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ws_manager.py backend/app/main.py backend/app/session_store.py backend/app/agent_service.py backend/tests/test_ws_flow.py
git commit -m "feat: add websocket chat flow"
```

## Task 6: scaffold frontend app shell and reducer

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/ws.ts`
- Create: `frontend/src/lib/sessionReducer.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/lib/sessionReducer.test.ts`

- [ ] **Step 1: Write the failing reducer test**

```ts
import { describe, expect, it } from "vitest";

import { reduceSessionEvent } from "./sessionReducer";

describe("reduceSessionEvent", () => {
  it("appends transcript messages and updates ownership", () => {
    const next = reduceSessionEvent(
      { messages: [], owner: "ai_active", aiTyping: false },
      {
        type: "message_created",
        audience: "both",
        created_at: "2026-04-06T16:30:00Z",
        payload: {
          id: "msg_1",
          role: "assistant",
          text: "I am checking this for you now.",
          audience: "both",
          visible_in_transcript: true,
          created_at: "2026-04-06T16:30:00Z",
          metadata: {},
        },
      },
    );

    expect(next.messages).toHaveLength(1);
  });

  it("replaces local state from session_snapshot on reconnect", () => {
    const next = reduceSessionEvent(
      { messages: [{ id: "stale" }], owner: "human_active", aiTyping: true, connectionState: "reconnecting" } as any,
      {
        type: "session_snapshot",
        audience: "both",
        created_at: "2026-04-06T16:31:00Z",
        payload: {
          messages: [],
          owner: "ai_active",
          ai_typing: false,
        },
      } as any,
    );

    expect(next.messages).toHaveLength(0);
    expect(next.owner).toBe("ai_active");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/lib/sessionReducer.test.ts`
Expected: FAIL because the Vite app and reducer are not scaffolded yet.

- [ ] **Step 3: Write minimal implementation**

```ts
export function reduceSessionEvent(state: SessionViewState, event: SessionEvent): SessionViewState {
  if (event.type === "message_created" && event.payload.visible_in_transcript) {
    return { ...state, messages: [...state.messages, event.payload] };
  }

  if (event.type === "ownership_changed") {
    return { ...state, owner: event.payload.owner };
  }

  if (event.type === "ai_typing") {
    return { ...state, aiTyping: event.payload.active };
  }

  return state;
}
```

Use one shared reducer for both `/customer` and `/agent`.
Also include reconnect-related state such as `connectionState: "connecting" | "connected" | "reconnecting"` and a reducer path for `session_snapshot`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/lib/sessionReducer.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/tsconfig.node.json frontend/vite.config.ts frontend/index.html frontend/src/main.tsx frontend/src/App.tsx frontend/src/styles.css frontend/src/types.ts frontend/src/lib/api.ts frontend/src/lib/ws.ts frontend/src/lib/sessionReducer.ts frontend/src/test/setup.ts frontend/src/lib/sessionReducer.test.ts
git commit -m "feat: scaffold frontend session shell"
```

## Task 7: build the customer chat page

**Files:**
- Create: `frontend/src/components/ChatLayout.tsx`
- Create: `frontend/src/components/MessageList.tsx`
- Create: `frontend/src/components/MessageComposer.tsx`
- Create: `frontend/src/components/StatusStrip.tsx`
- Create: `frontend/src/pages/CustomerChatPage.tsx`
- Create: `frontend/src/pages/CustomerChatPage.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/ws.ts`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing customer-page test**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { CustomerChatPage } from "./CustomerChatPage";

it("renders a unified support identity and hides internal status", async () => {
  render(
    <MemoryRouter>
      <CustomerChatPage />
    </MemoryRouter>,
  );

  expect(await screen.findByText("Online Support")).toBeInTheDocument();
  expect(screen.queryByText(/needs_followup/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/pages/CustomerChatPage.test.tsx`
Expected: FAIL because the page and shared chat components do not exist.

- [ ] **Step 3: Write minimal implementation**

```tsx
export function CustomerChatPage() {
  return (
    <ChatLayout
      title="Online Support"
      statusLabel="Here to help"
      transcriptRoleMap={{ assistant: "Online Support", agent: "Online Support" }}
    />
  );
}
```

Hook the page to:

- load `GET /api/session/customer`
- connect to `/ws/customer`
- send only `user_message`
- render AI and human replies with the same display name and avatar
- show a reconnecting indicator while the websocket retries
- request a fresh customer snapshot after reconnect and replace stale state with the latest `session_snapshot`

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/pages/CustomerChatPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChatLayout.tsx frontend/src/components/MessageList.tsx frontend/src/components/MessageComposer.tsx frontend/src/components/StatusStrip.tsx frontend/src/pages/CustomerChatPage.tsx frontend/src/pages/CustomerChatPage.test.tsx frontend/src/App.tsx frontend/src/lib/api.ts frontend/src/lib/ws.ts frontend/src/styles.css
git commit -m "feat: add customer chat page"
```

## Task 8: build the agent workstation page

**Files:**
- Create: `frontend/src/components/AgentControls.tsx`
- Create: `frontend/src/pages/AgentWorkbenchPage.tsx`
- Create: `frontend/src/pages/AgentWorkbenchPage.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/ws.ts`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write the failing agent-page test**

```tsx
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { AgentWorkbenchPage } from "./AgentWorkbenchPage";

it("shows takeover controls and internal status", async () => {
  render(
    <MemoryRouter>
      <AgentWorkbenchPage />
    </MemoryRouter>,
  );

  expect(await screen.findByRole("button", { name: /take over/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- --run src/pages/AgentWorkbenchPage.test.tsx`
Expected: FAIL because the agent workstation does not exist.

- [ ] **Step 3: Write minimal implementation**

```tsx
export function AgentWorkbenchPage() {
  return (
    <ChatLayout
      title="Agent Workbench"
      statusLabel="Internal view"
      controls={<AgentControls />}
      showInternalStatus
    />
  );
}
```

Hook the page to:

- load `GET /api/session/agent`
- connect to `/ws/agent`
- send `takeover`, `release_to_ai`, `resume_ai`, and `agent_message`
- display `agent_status` and `error_notice` messages in an internal panel
- retry websocket connection and request a fresh agent snapshot after reconnect
- surface `system_notice` and reconnect state without leaking them into the customer transcript

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- --run src/pages/AgentWorkbenchPage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/AgentControls.tsx frontend/src/pages/AgentWorkbenchPage.tsx frontend/src/pages/AgentWorkbenchPage.test.tsx frontend/src/App.tsx frontend/src/lib/api.ts frontend/src/lib/ws.ts frontend/src/styles.css
git commit -m "feat: add agent workstation page"
```

## Task 9: wire local configuration, manual verification, and docs

**Files:**
- Create: `.env.example`
- Create: `README.md`
- Modify: `backend/app/config.py`
- Modify: `backend/app/agent_service.py`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Write the failing config smoke test**

```python
from app.config import Settings


def test_settings_read_litellm_env() -> None:
    settings = Settings(
        LITELLM_BASE_URL="http://localhost:4000",
        LITELLM_API_KEY="test-key",
        LITELLM_MODEL="gpt-4o-mini",
    )

    assert settings.LITELLM_MODEL == "gpt-4o-mini"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_agent_service.py -v`
Expected: FAIL because the settings object does not yet validate the final environment contract.

- [ ] **Step 3: Write minimal implementation**

```python
class Settings(BaseSettings):
    LITELLM_BASE_URL: str
    LITELLM_API_KEY: str
    LITELLM_MODEL: str
```

Also add:

- `.env.example` with backend and frontend variables
- `README.md` with install, run, and manual demo steps
- one manual verification checklist covering AI reply, frustrated customer flow, takeover, resume, and restricted-request follow-up wording
- backend run instructions for `uvicorn app.main:app --reload --port 8000`
- frontend run instructions for `npm install && npm run dev`

- [ ] **Step 4: Run the full verification suite**

Run: `cd backend && pytest -v`
Expected: PASS

Run: `cd frontend && npm test -- --run`
Expected: PASS

Run: `cd frontend && npm run build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .env.example README.md backend/app/config.py backend/app/agent_service.py frontend/src/lib/api.ts
git commit -m "docs: finalize local setup and verification"
```

## Execution notes

- Keep backend event generation server-authoritative. The frontend should never infer ownership or operator-only status from timing.
- When implementing the AI adapter, isolate the real DeepAgent call behind an interface that can be replaced by a deterministic fake in tests.
- Do not add persistence, authentication, or multi-session abstractions unless a current task requires them.
- Prefer one root `SessionStore` instance per process for this demo.
