"""OpenAPI contract regression test (Phase 4, Task 5, AT-47)."""

import json
from pathlib import Path
from carecast.api.main import create_app
from carecast.settings import Settings


def test_openapi_contract_snapshot_matches():
    """Verify that current app.openapi() strictly matches tests/contract/openapi.snapshot.json."""
    settings = Settings(env="dev", enable_docs=True, db_path="data/carecast.db")
    app = create_app(settings)
    current_schema = app.openapi()

    snapshot_path = Path("tests/contract/openapi.snapshot.json")
    assert snapshot_path.exists(), "Snapshot file tests/contract/openapi.snapshot.json does not exist"

    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot_schema = json.load(f)

    assert current_schema == snapshot_schema, (
        "OpenAPI contract has changed compared to tests/contract/openapi.snapshot.json. "
        "Re-run scripts/generate_openapi_snapshot.py if this change was intentional."
    )
