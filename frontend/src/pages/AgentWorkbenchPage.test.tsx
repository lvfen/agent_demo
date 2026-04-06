import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { AgentWorkbenchPage } from "./AgentWorkbenchPage";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        messages: [],
        owner: "ai_active",
        ai_typing: false,
        agent_status: "normal",
        last_error: null
      })
    })
  );
});

it("shows takeover controls and internal status", async () => {
  render(
    <MemoryRouter>
      <AgentWorkbenchPage />
    </MemoryRouter>
  );

  expect(await screen.findByRole("button", { name: /take over/i })).toBeInTheDocument();
  expect(screen.getByText(/internal view/i)).toBeInTheDocument();
});
