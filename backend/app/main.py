from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.agent_service import SupportAgentService
from app.config import Settings
from app.session_store import SessionStore
from app.ws_manager import WebSocketManager

settings = Settings()
session_store = SessionStore()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def get_session_store() -> Generator[SessionStore, None, None]:
    yield session_store


@lru_cache(maxsize=1)
def get_support_agent_service() -> SupportAgentService:
    return SupportAgentService(settings=settings)


@lru_cache(maxsize=1)
def get_ws_manager() -> WebSocketManager:
    return WebSocketManager(store=session_store, agent_service=get_support_agent_service())


def reset_runtime_state() -> None:
    global session_store
    session_store = SessionStore()
    get_support_agent_service.cache_clear()
    get_ws_manager.cache_clear()


@app.get("/api/session/customer")
def customer_session(store: SessionStore = Depends(get_session_store)) -> dict:
    return store.build_snapshot(audience="customer")


@app.get("/api/session/agent")
def agent_session(store: SessionStore = Depends(get_session_store)) -> dict:
    return store.build_snapshot(audience="agent")


@app.websocket("/ws/customer")
async def customer_ws(websocket: WebSocket) -> None:
    manager = get_ws_manager()
    await manager.connect(websocket, audience="customer")
    await manager.handle_customer_loop(websocket)


@app.websocket("/ws/agent")
async def agent_ws(websocket: WebSocket) -> None:
    manager = get_ws_manager()
    await manager.connect(websocket, audience="agent")
    await manager.handle_agent_loop(websocket)
