"""Test reproducing multi-threaded SQLite ProgrammingError on production connect_ro path."""

import threading
from pathlib import Path
from carecast.db import connect_ro, connect_rw


def test_connect_ro_concurrent_thread_query(tmp_path: Path) -> None:
    """Production connect_ro must support querying from worker threads in async FastAPI."""
    db_file = tmp_path / "concurrent.db"
    seed = connect_rw(db_file)
    seed.execute("CREATE TABLE t (v INT);")
    seed.execute("INSERT INTO t VALUES (100);")
    seed.commit()
    seed.close()

    # Opened on current thread via production connect_ro (without check_same_thread=False)
    conn = connect_ro(db_file)
    results = []
    errors = []

    def run_query():
        try:
            rows = conn.execute("SELECT v FROM t;").fetchall()
            results.append(rows[0][0])
        except Exception as exc:
            errors.append(exc)

    thread = threading.Thread(target=run_query)
    thread.start()
    thread.join()

    # If sqlite3.ProgrammingError occurred, re-raise to fail the test
    if errors:
        raise errors[0]
    assert results == [100]
