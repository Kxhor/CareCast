"""Generate OpenAPI specification contract snapshot (Phase 4, Task 5)."""

import json
from pathlib import Path
from carecast.api.main import create_app
from carecast.settings import Settings


def main() -> None:
    settings = Settings(env="dev", enable_docs=True, db_path="data/carecast.db")
    app = create_app(settings)
    schema = app.openapi()

    out_dir = Path("tests/contract")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "openapi.snapshot.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, sort_keys=True)

    print(f"Successfully generated OpenAPI snapshot at {out_file} with {len(schema.get('paths', {}))} paths.")


if __name__ == "__main__":
    main()
