import os
import tempfile
import pytest

_test_db = tempfile.NamedTemporaryFile(suffix="_test_landsafe.db", delete=False)
_test_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db.name}"
os.environ.setdefault("LANDSAFE_MODE", "production")

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def isolate_test_db():
    from backend.app.core.database import init_db
    from backend.app.services.db_seeder import seed_database
    init_db()
    seed_database()
    yield
    try:
        if os.path.exists(_test_db.name):
            os.remove(_test_db.name)
    except Exception:
        pass


@pytest.fixture(scope="session")
def app():
    from backend.app.main import app as fastapi_app
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def no_network(monkeypatch):
    """Force every outbound HTTP call to fail.

    Nothing in the test suite is allowed to touch the network. This fixture makes
    that explicit rather than relying on the sandbox happening to be offline, so
    the NO DATA path is exercised deterministically on any machine.
    """
    import httpx

    async def _boom(*args, **kwargs):
        raise httpx.ConnectError("network disabled in tests")

    monkeypatch.setattr(httpx.AsyncClient, "get", _boom)
    return _boom
