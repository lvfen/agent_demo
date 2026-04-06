import type { SessionEvent, SessionViewState } from "../types";

export function reduceSessionEvent(state: SessionViewState, event: SessionEvent): SessionViewState {
  if (event.type === "message_created" && event.payload.visible_in_transcript) {
    return {
      ...state,
      messages: [...state.messages, event.payload]
    };
  }

  if (event.type === "ownership_changed") {
    return {
      ...state,
      owner: event.payload.owner
    };
  }

  if (event.type === "ai_typing") {
    return {
      ...state,
      aiTyping: event.payload.active
    };
  }

  if (event.type === "session_snapshot") {
    return {
      ...state,
      messages: event.payload.messages,
      owner: event.payload.owner,
      aiTyping: event.payload.ai_typing,
      connectionState: "connected",
      agentStatus: event.payload.agent_status,
      lastError: event.payload.last_error
    };
  }

  return state;
}
