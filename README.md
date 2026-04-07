# Customer service demo

Single-session customer-service demo with:

- `frontend/`: React + Vite customer chat page and agent workbench
- `backend/`: FastAPI API + WebSocket backend
- AI-first handling with a DeepAgent/LiteLLM integration path
- human takeover and return-to-AI controls

## Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

- Customer page: `http://localhost:5173/customer`
- Agent page: `http://localhost:5173/agent`

## Environment

Copy `.env.example` to `.env` at the repository root or export the variables in your shell:

- `LITELLM_BASE_URL`
- `LITELLM_API_KEY`
- `LITELLM_MODEL`
- `VITE_API_BASE_URL`
- `VITE_WS_BASE_URL`

If your LiteLLM route is specifically exposing Gemini, the backend also accepts:

- `GEMINI_BASE_URL`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`

## Demo flow

1. Start backend and frontend.
2. Open `/customer` and `/agent` in two tabs.
3. Send a customer message from the customer page.
4. Use `Take Over` in the agent workbench to switch to manual handling.
5. Use `Return to AI` to hand the conversation back.
6. Send a restricted request such as "I want a refund" to trigger internal follow-up and a customer-safe holding reply.

## Verification

Backend:

```bash
cd backend
pytest -v
```

Frontend:

```bash
cd frontend
npm test -- --run
npm run build
```
