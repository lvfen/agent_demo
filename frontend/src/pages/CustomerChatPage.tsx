import { useEffect, useMemo, useRef, useState } from "react";

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
  connectionState: "connecting"
};

const roleMap = {
  assistant: "Online Support",
  agent: "Online Support",
  user: "You",
  system: "Online Support"
} satisfies Partial<Record<TranscriptMessage["role"], string>>;

export function CustomerChatPage() {
  const [state, setState] = useState<SessionViewState>(initialState);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadSnapshot() {
      const response = await fetch(`${API_BASE_URL}/api/session/customer`);
      const payload = await response.json();
      if (!isMounted) {
        return;
      }
      setState((current) =>
        reduceSessionEvent(current, {
          type: "session_snapshot",
          audience: "customer",
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

    const socket = new WebSocket(buildWebSocketUrl("/ws/customer"));
    socketRef.current = socket;

    socket.onopen = () => {
      setState((current) => ({ ...current, connectionState: "connected" }));
    };

    socket.onclose = () => {
      setState((current) => ({ ...current, connectionState: "reconnecting" }));
    };

    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as SessionEvent;
      setState((current) => reduceSessionEvent(current, event));
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, []);

  const statusLabel = useMemo(() => {
    if (state.connectionState === "reconnecting") {
      return "Reconnecting to support...";
    }
    if (state.aiTyping) {
      return "Checking this for you...";
    }
    return "Here to help";
  }, [state.aiTyping, state.connectionState]);

  const handleSend = (text: string) => {
    socketRef.current?.send(JSON.stringify({ type: "user_message", payload: { text } }));
  };

  return (
    <ChatLayout title="Online Support" subtitle="Always-on customer support">
      <StatusStrip label={statusLabel} />
      <MessageList messages={state.messages} transcriptRoleMap={roleMap} />
      <MessageComposer
        placeholder="Type your message"
        submitLabel="Send"
        disabled={state.connectionState === "reconnecting"}
        onSubmit={handleSend}
      />
    </ChatLayout>
  );
}
