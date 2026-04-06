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
        agent_customer_message = agent.receive_json()
        agent_holding_message = agent.receive_json()
        paused_notice = agent.receive_json()

        assert agent_customer_message["type"] == "message_created"
        assert agent_holding_message["type"] == "message_created"
        assert paused_notice["type"] == "system_notice"
        assert customer_message["type"] == "message_created"
        assert customer_holding["type"] == "message_created"
        assert "checking" in customer_holding["payload"]["text"].lower()

        agent.send_json({"type": "resume_ai", "payload": {}})
        ownership_event = agent.receive_json()
        assert ownership_event["payload"]["owner"] == "ai_active"


def test_customer_socket_never_receives_agent_only_notice() -> None:
    client = TestClient(app)

    with client.websocket_connect("/ws/customer") as customer, client.websocket_connect("/ws/agent") as agent:
        customer.receive_json()
        agent.receive_json()

        customer.send_json({"type": "user_message", "payload": {"text": "I want a refund"}})

        first_event = customer.receive_json()
        second_event = customer.receive_json()

        assert first_event["audience"] != "agent"
        assert second_event["audience"] != "agent"
