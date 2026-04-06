export type Audience = "customer" | "agent" | "both";
export type OwnerState = "ai_active" | "human_active" | "ai_paused";
export type ConnectionState = "connecting" | "connected" | "reconnecting";

export type TranscriptMessage = {
  id: string;
  role: "user" | "assistant" | "agent" | "system";
  text: string;
  audience: Audience;
  visible_in_transcript: boolean;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type SessionSnapshotPayload = {
  session_id?: string;
  messages: TranscriptMessage[];
  owner: OwnerState;
  ai_typing: boolean;
  agent_status?: string;
  last_error?: string | null;
};

export type SessionEvent =
  | {
      type: "message_created";
      audience: Audience;
      created_at: string;
      payload: TranscriptMessage;
    }
  | {
      type: "ownership_changed";
      audience: Audience;
      created_at: string;
      payload: { owner: OwnerState; reason: string };
    }
  | {
      type: "ai_typing";
      audience: Audience;
      created_at: string;
      payload: { active: boolean };
    }
  | {
      type: "session_snapshot";
      audience: Audience;
      created_at: string;
      payload: SessionSnapshotPayload;
    }
  | {
      type: "system_notice" | "error_notice";
      audience: Audience;
      created_at: string;
      payload: Record<string, unknown>;
    };

export type SessionViewState = {
  messages: TranscriptMessage[];
  owner: OwnerState;
  aiTyping: boolean;
  connectionState: ConnectionState;
  agentStatus?: string;
  lastError?: string | null;
};
