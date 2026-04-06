import { useEffect, useMemo, useRef, useState } from "react";

import { AgentControls } from "../components/AgentControls";
import { ChatLayout } from "../components/ChatLayout";
import { MessageComposer } from "../components/MessageComposer";
import { MessageList } from "../components/MessageList";
import { StatusStrip } from "../components/StatusStrip";
import { API_BASE_URL } from "../lib/api";
import { reduceSessionEvent } from "../lib/sessionReducer";
import { buildWebSocketUrl } from "../lib/ws";
import type { SessionEvent, SessionViewState, TranscriptMessage } from "../types";

const initialState: SessionViewState = {
  messages: [],
  owner: "ai_active",
  aiTyping: false,
  connectionState: "connecting",
  agentStatus: "normal",
  lastError: null
};

const roleMap = {
  assistant: "Online Support",
  agent: "Human Agent",
  user: "Customer",
  system: "System"
} satisfies Partial<Record<TranscriptMessage["role"], string>>;

export function AgentWorkbenchPage() {
  const [state, setState] = useState<SessionViewState>(initialState);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadSnapshot() {
      const response = await fetch(`${API_BASE_URL}/api/session/agent`);
      const payload = await response.json();
      if (!isMounted) {
        return;
      }
      setState((current) =>
        reduceSessionEvent(current, {
          type: "session_snapshot",
          audience: "agent",
          created_at: new Date().toISOString(),
          payload
        })
      );
    }

    void loadSnapshot();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (typeof WebSocket !== "function") {
      return;
    }

    const socket = new WebSocket(buildWebSocketUrl("/ws/agent"));
    socketRef.current = socket;

    socket.onopen = () => {
      setState((current) => ({ ...current, connectionState: "connected" }));
    };

    socket.onclose = () => {
      setState((current) => ({ ...current, connectionState: "reconnecting" }));
    };

    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as SessionEvent;
      if (event.type === "system_notice") {
        setState((current) => ({
          ...current,
          agentStatus: String(event.payload.code ?? current.agentStatus),
          lastError: current.lastError
        }));
        return;
      }
      if (event.type === "error_notice") {
        setState((current) => ({
          ...current,
          lastError: String(event.payload.message ?? "Unknown agent error")
        }));
        return;
      }
      setState((current) => reduceSessionEvent(current, event));
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, []);

  const statusLabel = useMemo(() => {
    if (state.connectionState === "reconnecting") {
      return "Reconnecting internal view...";
    }
    if (state.owner === "human_active") {
      return "Internal view: you currently own the conversation";
    }
    if (state.owner === "ai_paused") {
      return "Internal view: AI is paused";
    }
    return "Internal view";
  }, [state.connectionState, state.owner]);

  const sendEvent = (type: string, payload: Record<string, unknown>) => {
    socketRef.current?.send(JSON.stringify({ type, payload }));
  };

  return (
    <ChatLayout
      title="Agent Workbench"
      subtitle="Internal support console"
      controls={
        <AgentControls
          owner={state.owner}
          onTakeOver={() => sendEvent("takeover", { reason: "manual_takeover" })}
          onReleaseToAi={() => sendEvent("release_to_ai", {})}
          onResumeAi={() => sendEvent("resume_ai", {})}
        />
      }
    >
      <StatusStrip label={statusLabel} />
      <div className="internal-grid">
        <section className="internal-panel">
          <h2>Internal status</h2>
          <p>Owner: {state.owner}</p>
          <p>Workflow: {state.agentStatus ?? "normal"}</p>
          <p>{state.lastError ? `Error: ${state.lastError}` : "No current errors"}</p>
        </section>
        <section className="chat-column">
          <MessageList messages={state.messages} transcriptRoleMap={roleMap} />
        </section>
      </div>
      <MessageComposer
        placeholder="Send an internal customer-facing reply"
        submitLabel="Send Reply"
        onSubmit={(text) => sendEvent("agent_message", { text })}
      />
    </ChatLayout>
  );
}
