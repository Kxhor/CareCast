"""Smoke tests for CareCast package."""

import carecast
import carecast.db
import carecast.settings


def test_import_carecast() -> None:
    """Verify carecast imports cleanly and exposes package version."""
    assert carecast.__version__ == "0.1.0"
    assert hasattr(carecast, "__name__")


def test_import_submodules() -> None:
    """Verify core submodules can be imported."""
    assert hasattr(carecast.settings, "get_settings")
    assert hasattr(carecast.db, "connect_rw")
    assert hasattr(carecast.db, "connect_ro")
