"""T4: Verify /api/v1/meta returns all quality issues, not a truncated subset."""
import sqlite3
import pytest

from carecast.api.main import create_app
from carecast.settings import Settings


@pytest.fixture(scope="module")
def client():
    from starlette.testclient import TestClient
    app = create_app(Settings())
    with TestClient(app) as c:
        yield c


def test_quality_issues_count_matches_db(client):
    """API quality_issues count must equal DB row count."""
    conn = sqlite3.connect("file:data/carecast.db?mode=ro", uri=True)
    db_count = conn.execute("SELECT COUNT(*) FROM data_quality_issues").fetchone()[0]
    conn.close()

    resp = client.get("/api/v1/meta")
    assert resp.status_code == 200
    api_count = len(resp.json()["quality_issues"])
    assert api_count == db_count, f"API returned {api_count} but DB has {db_count}"
