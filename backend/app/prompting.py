from app.models import AgentStatus, Message

SUPPORT_SYSTEM_PROMPT = """
You are an online customer-service representative.
Do not say you are an AI, model, assistant, or bot.
Keep one continuous support identity even when the case needs internal follow-up.
When the customer is upset, acknowledge the frustration directly, restate the issue simply, and say what you are doing next.
Avoid stock filler, over-structured replies, and robotic wording.
If the request is restricted or needs internal handling, reply in a customer-safe way like you are checking it, without mentioning transfer to AI or human.
""".strip()


def build_support_messages(messages: list[Message], summary: str, agent_status: AgentStatus) -> list[dict[str, str]]:
    prompt_messages = [{"role": "system", "content": SUPPORT_SYSTEM_PROMPT}]
    if summary:
        prompt_messages.append(
            {
                "role": "system",
                "content": f"Conversation summary: {summary}",
            }
        )
    prompt_messages.append(
        {
            "role": "system",
            "content": f"Internal status: {agent_status}",
        }
    )
    prompt_messages.extend({"role": message.role if message.role != "agent" else "assistant", "content": message.text} for message in messages)
    return prompt_messages
