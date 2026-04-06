from fastapi.testclient import TestClient

from app.main import app
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
