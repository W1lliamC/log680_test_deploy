"""
Unified pytest configuration for unit (in-process) and integration (live server) tests.
- Unit tests: use SQLite temp DB + FastAPI TestClient
- Integration tests: use httpx client against a running server (health-checked)
"""

from __future__ import annotations

import os
import time
import typing as t

import httpx
import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Global test env
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _test_env() -> None:
    """Set basic test environment defaults."""
    os.environ.setdefault("TESTING", "1")
    # Safe default to avoid accidental real calls; override in env if needed.
    os.environ.setdefault("TOKEN_GITHUB", "unit-test-token")


# ---------------------------------------------------------------------------
# Unit-test DB engine binding (SQLite) + metadata creation
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def _unit_engine(tmp_path_factory) -> Engine:
    """Create a single SQLite engine for all in-process/unit tests."""
    db_dir = tmp_path_factory.mktemp("db_unit")
    dsn = f"sqlite:///{db_dir/'unit.db'}"

    engine = create_engine(
        dsn,
        connect_args={"check_same_thread": False},
        future=True,
    )
    return engine


@pytest.fixture(scope="session", autouse=True)
def _bind_sessionlocal_and_create_schema(_unit_engine: Engine) -> None:
    """
    Bind the global SessionLocal to the SQLite engine and create tables once.
    This runs for any test session so application code can call SessionLocal().
    """
    import src.services.db as dbmod
    from src.services.db import Base

    # Force the app's DB accessors to use our test engine
    dbmod._engine = _unit_engine
    dbmod.get_engine = lambda: _unit_engine  # type: ignore[assignment]
    # If SessionLocal is a sessionmaker, make sure it's bound
    try:
        dbmod.SessionLocal.configure(bind=_unit_engine)  # type: ignore[attr-defined]
    except Exception:
        # If SessionLocal is a function returning a Session, ignore
        pass

    # Create the schema
    Base.metadata.create_all(bind=_unit_engine)


# ---------------------------------------------------------------------------
# FastAPI app + in-process TestClient (unit tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    """Import the FastAPI app after DB is ready (unit tests)."""
    # Import late so the app sees the bound engine/session
    from src.app import app as fastapi_app

    return fastapi_app


@pytest.fixture()
def client(app):
    """FastAPI in-process client (unit tests)."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Integration test options/fixtures (live server)
# ---------------------------------------------------------------------------


def pytest_addoption(parser):
    parser.addoption(
        "--base-url",
        action="store",
        default=os.getenv("BASE_URL", "http://localhost:8000"),
        help="Base URL of the running server for integration tests",
    )


@pytest.fixture(scope="session")
def base_url(pytestconfig) -> str:
    """Base URL for integration tests (override via --base-url)."""
    return t.cast(str, pytestconfig.getoption("--base-url"))


def _is_server_running(base_url: str) -> bool:
    """Light health probe to decide whether to run integration tests."""
    try:
        resp = requests.get(f"{base_url}/health", timeout=2.0)
        return resp.status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def live_client(base_url: str):
    """
    httpx.Client pointed at a running server.

    If the server is not reachable, integration tests that depend on this
    fixture will be skipped automatically.
    """
    timeout = float(os.getenv("TEST_TIMEOUT", "60"))
    try:
        with httpx.Client(base_url=base_url, timeout=5.0) as probe:
            probe.get("/health")
    except Exception:
        pytest.skip(
            f"Server not reachable at {base_url}. Start it for integration tests."
        )
    # Provide a client for the whole session; user tests can create/delete data as needed.
    client = httpx.Client(base_url=base_url, timeout=timeout)
    yield client
    client.close()


# ---------------------------------------------------------------------------
# Integration helper (kept from your original)
# ---------------------------------------------------------------------------


class IntegrationTestHelper:
    """Helper for common integration test operations against a live server."""

    def __init__(self, client: httpx.Client):
        self.client = client

    def wait_for_response(
        self, url: str, expected_status: int = 200, timeout: int = 10
    ) -> bool:
        """Poll an endpoint until it returns expected_status or timeout occurs."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                r = self.client.get(url)
                if r.status_code == expected_status:
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def create_test_data(self) -> dict:
        """Stub: extend to create remote test data if your API allows it."""
        return {"message": "Test data creation would go here"}


@pytest.fixture
def integration_helper(live_client) -> IntegrationTestHelper:
    """Convenience helper for integration tests."""
    return IntegrationTestHelper(live_client)
