from collections.abc import Generator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.session_store import SessionStore

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


@app.get("/api/session/customer")
def customer_session(store: SessionStore = Depends(get_session_store)) -> dict:
    return store.build_snapshot(audience="customer")


@app.get("/api/session/agent")
def agent_session(store: SessionStore = Depends(get_session_store)) -> dict:
    return store.build_snapshot(audience="agent")
