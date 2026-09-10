import os



import pytest

from fastapi.testclient import TestClient



from app.services.database import init_schema, truncate_all_tables





@pytest.fixture()

def client(monkeypatch) -> TestClient:

    """Requires PostgreSQL; default DSN matches backend/docker-compose.yml (database bloom_test)."""

    monkeypatch.setenv(

        "BLOOM_DATABASE_URL",

        os.environ.get(

            "BLOOM_TEST_DATABASE_URL",

            "postgresql://bloom:bloom@127.0.0.1:5433/bloom_test",

        ),

    )

    monkeypatch.setenv("BLOOM_ENABLE_ANALYSIS_HISTORY", "true")

    monkeypatch.setenv("BLOOM_JWT_SECRET", "test-secret")



    init_schema()

    truncate_all_tables()



    from app.main import app



    yield TestClient(app)



    truncate_all_tables()





def auth_header(token: str) -> dict[str, str]:

    return {"Authorization": f"Bearer {token}"}





@pytest.fixture()

def register_and_login(client: TestClient):

    def _do(username: str = "alice", password: str = "pw12345") -> dict:

        r = client.post("/api/auth/register", json={"username": username, "password": password})

        assert r.status_code == 200, r.text

        return r.json()



    return _do
