# 2026-04-06 customer service demo design

## Overview

Build a single-conversation customer-service demo in the current directory.

The demo has two frontend pages and one Python backend:

- A customer chat page that looks like a normal customer-service chat window
- An agent workstation page for a human operator
- A FastAPI backend that supports both AI-driven replies and human takeover

The conversation starts with AI handling the customer by default. A human operator can take over the same live conversation at any time, then release it back to AI later.

The customer must feel they are always talking to one customer-service representative. The system must not expose "you are talking to AI now" or "this has been switched to a human now" in user-facing copy.

## Goals

- Deliver a runnable end-to-end demo with one live conversation
- Support real LLM-backed replies through LangChain DeepAgent and a LiteLLM proxy
- Support human 1v1 live chat through a separate agent workstation page
- Preserve in-memory conversation history during the app runtime
- Make AI replies sound like a real support agent rather than an assistant bot
- Handle upset customers by acknowledging frustration and continuing the thread naturally
- Route requests outside AI authority into an internal escalation path without exposing implementation details to the customer

## Non-goals

- Multi-session routing or queue management
- Multi-agent assignment
- Persistent storage across restarts
- User login or operator login
- CRM, ticketing, or back-office system integration
- Analytics, dashboards, or reporting

## Product constraints

- Exactly one active conversation exists in the demo
- The customer page and the agent page both connect to the same conversation
- The customer enters through the AI-handled path by default
- The human operator can take over in real time
- The human operator can release the conversation back to AI
- If AI fails, times out, or reaches a limitation, the customer still sees a unified support identity

## User-facing behavior

### Customer page

The customer page presents a normal support chat UI with:

- A header showing a generic support identity such as "online support"
- A message timeline
- A text input and send action
- Lightweight status text such as "checking this for you" or "replying"

The customer page never shows:

- "AI mode"
- "handoff to human"
- raw technical errors
- model names, proxy names, or stack traces

### Agent page

The agent page presents an operator-facing workstation with:

- The same live message timeline
- Current ownership state
- A `Take Over` action
- A `Return to AI` action
- A text input for human replies
- Internal status markers for escalation or follow-up

The human operator sees internal workflow state. The customer does not.

## Architecture

### Frontend

Use React with Vite.

Create two routes or entry pages:

- `/customer`
- `/agent`

Each page:

- Loads the current session snapshot through HTTP on first render
- Connects to the backend through WebSocket
- Renders the same canonical event stream from the backend

### Backend

Use FastAPI as the single backend process.

Responsibilities:

- Keep the single session state in memory
- Accept customer and human-agent WebSocket connections
- Broadcast message and ownership events to both pages
- Call the LangChain DeepAgent flow when AI owns the session
- Cancel or discard AI replies when ownership changes during generation
- Expose a small HTTP API for bootstrapping and health checks

### AI layer

Use LangChain DeepAgent with a LiteLLM-backed model connection.

Configuration is provided through environment variables, including:

- LiteLLM base URL
- LiteLLM API key
- model name

## Session model

The backend stores one in-memory session object with at least these fields:

- `session_id`
- `messages`
- `owner`
- `agent_status`
- `handoff_reason`
- `conversation_summary`
- `ai_reply_task`
- `last_error`

### Ownership states

Use these ownership states:

- `ai_active`: AI should answer customer messages
- `human_active`: only the human operator should answer
- `ai_paused`: AI should not answer until explicitly resumed

Default state is `ai_active`.

### Supporting internal states

Track internal workflow states such as:

- `normal`
- `needs_followup`
- `escalated_backoffice`
- `waiting_human`

These states are internal only. They may affect operator UI and backend behavior, but they must not be shown to the customer as implementation details.

## API design

### HTTP endpoints

- `GET /api/health`
  Returns a simple health response.

- `GET /api/session`
  Returns the current session snapshot, including message history, owner, and internal flags needed by the frontend.

### WebSocket endpoints

- `/ws/customer`
  Customer channel. Accepts customer-originated messages.

- `/ws/agent`
  Operator channel. Accepts human messages and control actions.

### Client-to-server events

Customer may send:

- `user_message`

Agent may send:

- `agent_message`
- `takeover`
- `release_to_ai`

### Server-to-client events

Broadcast standard events to both pages:

- `session_snapshot`
- `message_created`
- `ownership_changed`
- `ai_typing`
- `system_notice`
- `error_notice`

The frontend should treat the backend event stream as the single source of truth.

## Message flow

### Customer message while AI owns the session

1. Customer sends `user_message`
2. Backend appends it to memory
3. Backend broadcasts `message_created`
4. Backend starts an async AI reply task
5. Backend broadcasts `ai_typing`
6. AI returns a support-style reply
7. Backend appends the AI reply
8. Backend broadcasts the reply as `message_created`

### Human takeover

1. Agent page sends `takeover`
2. Backend changes owner to `human_active`
3. Backend cancels or invalidates any in-flight AI reply task
4. Backend broadcasts `ownership_changed`
5. Customer messages continue to appear in the thread, but do not trigger AI replies
6. Human replies are broadcast as normal messages

### Return to AI

1. Agent page sends `release_to_ai`
2. Backend changes owner to `ai_active`
3. Backend broadcasts `ownership_changed`
4. Future customer messages trigger AI replies again

## AI support-agent behavior

### Identity

The AI is instructed to act as a customer-service representative, not as an AI assistant.

It must not say things like:

- "as an AI"
- "I am just a model"
- "I cannot feel"
- "I cannot access that because I am an AI"

It should respond as one continuous support identity that can continue handling the case or continue checking internally.

### History handling

Each AI turn uses:

- recent message history
- a lightweight rolling summary
- current internal state flags

The summary should capture:

- unresolved issue
- customer sentiment
- prior promises made to the customer
- whether follow-up or internal escalation is already in progress

This allows the next reply to continue the thread naturally rather than sounding like a reset.

### Upset-customer handling

When the customer is frustrated, the AI should:

- acknowledge the frustration directly
- avoid defensive or robotic wording
- restate the current issue in plain language
- tell the customer what it is doing next
- avoid over-apologizing or using empty filler

### Humanized writing

Apply the spirit of the `humanizer` skill to outbound AI copy.

Requirements:

- avoid template-heavy support phrasing
- avoid over-structured three-part replies
- avoid inflated or overly polished language
- avoid "hope this helps", "thanks for your patience", and similar stock fillers unless context makes them sound natural
- prefer short, direct, plain-language replies
- vary rhythm enough that the chat does not read like a generated template

Implementation note:

Use prompt constraints first. Optionally apply a lightweight post-processing pass to catch obvious AI tells, but do not rewrite so aggressively that meaning changes.

## Escalation and failure policy

### Internal escalation

If the request is outside AI authority or should not be answered automatically, the backend marks an internal follow-up state such as `needs_followup` or `escalated_backoffice`.

Triggers may include:

- refund or compensation requests
- account-sensitive changes
- requests for restricted backend data
- repeated unresolved frustration
- low-confidence or high-risk answer conditions

### Customer-visible wording

Customer-visible wording must preserve a single support identity.

Allowed style:

- "I am checking this for you now."
- "I am confirming this on my side. Give me a moment."
- "I am following up on this and will come back shortly."

Not allowed:

- "I am transferring you to a human agent."
- "The AI cannot process this."
- "A different support representative will continue this."

The customer should feel the same support thread is continuing, even if the internal owner changes.

### Model failure

If the LiteLLM call fails, times out, or returns unusable output:

- do not expose the failure directly to the customer
- set an internal follow-up state
- send a support-style holding reply if appropriate
- allow the human operator to continue the thread naturally from the workstation

## Frontend details

### Customer page

Needed UI sections:

- header
- chat transcript
- typing/status indicator
- input composer

Behavior:

- show incoming replies in real time
- show neutral support-status messaging
- keep visual language consistent whether the backend owner is AI or human

### Agent page

Needed UI sections:

- ownership control bar
- chat transcript
- internal status panel
- human reply composer

Behavior:

- display whether AI or human currently owns the thread
- let the operator take over or return control
- show internal state markers such as follow-up needed
- never rely on local guesses; only reflect backend events

## Error handling

- On WebSocket disconnect, show reconnecting state and retry automatically
- On reconnect, fetch or receive a fresh session snapshot
- If duplicate AI replies race with a takeover, drop stale AI output
- If no operator page is open, the system should still run in AI mode
- If the operator takes over while AI is typing, only one final reply may appear, never both

## Verification scenarios

The implementation is complete when these scenarios work:

1. Customer enters and receives AI replies through the live model connection
2. Customer sends multiple unhappy messages and the AI carries context forward naturally
3. Operator takes over and AI stops replying immediately
4. Operator returns the conversation to AI and AI resumes on the next customer message
5. AI reaches a restricted or high-risk request and responds with unified support wording while marking internal follow-up state

## Suggested project structure

```text
frontend/
  src/
    pages/
      CustomerChat.tsx
      AgentWorkbench.tsx
    components/
    lib/
backend/
  app/
    main.py
    api.py
    ws.py
    session_store.py
    agent_service.py
    prompting.py
docs/
  superpowers/
    specs/
```

## Open implementation decisions already resolved

- Frontend stack: React + Vite
- Backend stack: FastAPI
- Realtime transport: WebSocket
- Storage for demo: in-memory only
- Session scope: one conversation only
- Default routing: AI first, human can take over, then return control to AI

## Out of scope for the first implementation plan

- Persistence across restart
- Authentication
- Multiple simultaneous conversations
- Multiple human operators
- Suggestion-assist mode for human operators
- Ticket system integration
