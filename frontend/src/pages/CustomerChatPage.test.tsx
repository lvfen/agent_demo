import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { CustomerChatPage } from "./CustomerChatPage";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        messages: [],
        owner: "ai_active",
        ai_typing: false
      })
    })
  );
});

it("renders a unified support identity and hides internal status", async () => {
  render(
    <MemoryRouter>
      <CustomerChatPage />
    </MemoryRouter>
  );

  expect(await screen.findByText("Online Support")).toBeInTheDocument();
  expect(screen.queryByText(/needs_followup/i)).not.toBeInTheDocument();
});
