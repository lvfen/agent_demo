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
