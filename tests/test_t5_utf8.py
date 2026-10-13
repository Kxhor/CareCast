"""T5: Verify capacity note from /api/v1/meta decodes as valid UTF-8."""
import pytest

from carecast.api.main import create_app
from carecast.settings import Settings


@pytest.fixture(scope="module")
def client():
    from starlette.testclient import TestClient
    app = create_app(Settings())
    with TestClient(app) as c:
        yield c


def test_meta_capacity_note_utf8(client):
    """defaults.capacity.note must be valid UTF-8 text containing em-dash."""
    resp = client.get("/api/v1/meta")
    assert resp.status_code == 200
    note = resp.json()["defaults"]["capacity"]["note"]
    # Roundtrip encode/decode to verify valid UTF-8
    encoded = note.encode("utf-8")
    decoded = encoded.decode("utf-8")
    assert decoded == note
    # Assert em-dash exists intact
    assert "\u2014" in note
