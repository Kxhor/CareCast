"""Unit tests for settings loader and validation."""

from pathlib import Path
import pytest

from carecast.settings import Settings, get_settings, load_toml


def test_default_settings() -> None:
    """Verify default settings align with TRD §8."""
    s = get_settings({})
    assert s.env == "prod"
    assert s.db_path == Path("data/carecast.db")
    assert s.enable_docs is False
    assert s.rate_get_per_min == 60
    assert s.rate_post_per_min == 20
    assert s.trusted_proxy is False
    assert s.hsts is False
    assert s.log_level == "INFO"


def test_custom_settings_via_env() -> None:
    """Verify settings can be overridden via environment mapping."""
    env = {
        "CARECAST_ENV": "dev",
        "CARECAST_DB_PATH": "custom/test.db",
        "CARECAST_ENABLE_DOCS": "1",
        "CARECAST_RATE_GET_PER_MIN": "120",
        "CARECAST_RATE_POST_PER_MIN": "40",
        "CARECAST_TRUSTED_PROXY": "true",
        "CARECAST_HSTS": "1",
        "CARECAST_LOG_LEVEL": "DEBUG",
    }
    s = get_settings(env)
    assert s.env == "dev"
    assert s.db_path == Path("custom/test.db")
    assert s.enable_docs is True
    assert s.rate_get_per_min == 120
    assert s.rate_post_per_min == 40
    assert s.trusted_proxy is True
    assert s.hsts is True
    assert s.log_level == "DEBUG"


def test_docs_disabled_in_prod() -> None:
    """Verify interactive docs cannot be enabled in prod environment."""
    env = {
        "CARECAST_ENV": "prod",
        "CARECAST_ENABLE_DOCS": "1",
    }
    s = get_settings(env)
    assert s.enable_docs is False


def test_reject_invalid_env() -> None:
    """Verify clear error when CARECAST_ENV is invalid."""
    with pytest.raises(ValueError, match="Invalid CARECAST_ENV"):
        get_settings({"CARECAST_ENV": "staging"})


def test_reject_invalid_rate_limit() -> None:
    """Verify clear error when rate limits are non-positive or non-integer."""
    with pytest.raises(ValueError, match="positive integer"):
        get_settings({"CARECAST_RATE_GET_PER_MIN": "0"})

    with pytest.raises(ValueError, match="positive integer"):
        get_settings({"CARECAST_RATE_GET_PER_MIN": "-10"})

    with pytest.raises(ValueError, match="Invalid integer"):
        get_settings({"CARECAST_RATE_POST_PER_MIN": "abc"})


def test_reject_invalid_log_level() -> None:
    """Verify clear error when CARECAST_LOG_LEVEL is unrecognized."""
    with pytest.raises(ValueError, match="Invalid CARECAST_LOG_LEVEL"):
        get_settings({"CARECAST_LOG_LEVEL": "VERBOSE"})


def test_reject_db_path_inside_web() -> None:
    """Verify rejection when DB path is inside the web directory."""
    with pytest.raises(ValueError, match="outside the web/ directory"):
        get_settings({"CARECAST_DB_PATH": "web/data.db"})


def test_load_toml_missing_file() -> None:
    """Verify FileNotFoundError when target TOML file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_toml("non_existent_config.toml")
