import { describe, expect, it } from "vitest";

import { reduceSessionEvent } from "./sessionReducer";

describe("reduceSessionEvent", () => {
  it("appends transcript messages and updates ownership", () => {
    const next = reduceSessionEvent(
      { messages: [], owner: "ai_active", aiTyping: false, connectionState: "connected" },
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
          metadata: {}
        }
      }
    );

    expect(next.messages).toHaveLength(1);
  });

  it("replaces local state from session_snapshot on reconnect", () => {
    const next = reduceSessionEvent(
      {
        messages: [
          {
            id: "stale",
            role: "assistant",
            text: "stale",
            audience: "both",
            visible_in_transcript: true,
            created_at: "2026-04-06T16:20:00Z",
            metadata: {}
          }
        ],
        owner: "human_active",
        aiTyping: true,
        connectionState: "reconnecting"
      },
      {
        type: "session_snapshot",
        audience: "both",
        created_at: "2026-04-06T16:31:00Z",
        payload: {
          messages: [],
          owner: "ai_active",
          ai_typing: false
        }
      }
    );

    expect(next.messages).toHaveLength(0);
    expect(next.owner).toBe("ai_active");
  });
});
