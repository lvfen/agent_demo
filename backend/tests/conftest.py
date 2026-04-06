import pytest

from app.main import reset_runtime_state


@pytest.fixture(autouse=True)
def reset_backend_runtime() -> None:
    reset_runtime_state()
