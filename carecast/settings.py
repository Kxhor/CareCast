"""CareCast configuration and settings loader.

Loads configuration from process environment variables and optional TOML files.
Fails fast with clear ValueError exceptions on invalid configuration.
Conforms to TRD §8. No secrets are handled or required.
"""

from __future__ import annotations

import os
from pathlib import Path
import tomllib
from typing import Any

VALID_ENVS = {"prod", "dev", "test"}
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class Settings:
    """Immutable application settings container."""

    def __init__(
        self,
        env: str = "prod",
        db_path: Path | str = "data/carecast.db",
        enable_docs: bool = False,
        rate_get_per_min: int = 60,
        rate_post_per_min: int = 20,
        trusted_proxy: bool = False,
        hsts: bool = False,
        log_level: str = "INFO",
    ) -> None:
        # Validate env
        env_clean = env.strip().lower()
        if env_clean not in VALID_ENVS:
            raise ValueError(
                f"Invalid CARECAST_ENV='{env}'. Must be one of: {sorted(VALID_ENVS)}"
            )
        self.env = env_clean

        # Validate db_path
        path_obj = Path(db_path)
        # Check path is outside web directory
        try:
            resolved_db = path_obj.resolve()
            web_dir = Path("web").resolve()
            if resolved_db == web_dir or web_dir in resolved_db.parents:
                raise ValueError("CARECAST_DB_PATH must be outside the web/ directory")
        except RuntimeError:
            pass
        self.db_path = path_obj

        # Validate enable_docs: only allowed in dev environment
        self.enable_docs = bool(enable_docs) and (self.env == "dev")

        # Validate rates
        if not isinstance(rate_get_per_min, int) or rate_get_per_min <= 0:
            raise ValueError(
                f"CARECAST_RATE_GET_PER_MIN must be a positive integer, got: {rate_get_per_min}"
            )
        self.rate_get_per_min = rate_get_per_min

        if not isinstance(rate_post_per_min, int) or rate_post_per_min <= 0:
            raise ValueError(
                f"CARECAST_RATE_POST_PER_MIN must be a positive integer, got: {rate_post_per_min}"
            )
        self.rate_post_per_min = rate_post_per_min

        # Validate flags
        self.trusted_proxy = bool(trusted_proxy)
        self.hsts = bool(hsts)

        # Validate log level
        level_clean = log_level.strip().upper()
        if level_clean not in VALID_LOG_LEVELS:
            raise ValueError(
                f"Invalid CARECAST_LOG_LEVEL='{log_level}'. Must be one of: {sorted(VALID_LOG_LEVELS)}"
            )
        self.log_level = level_clean

    def __repr__(self) -> str:
        return (
            f"Settings(env='{self.env}', db_path='{self.db_path}', "
            f"enable_docs={self.enable_docs}, rate_get={self.rate_get_per_min}, "
            f"rate_post={self.rate_post_per_min}, trusted_proxy={self.trusted_proxy}, "
            f"hsts={self.hsts}, log_level='{self.log_level}')"
        )


def _parse_bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    v = val.strip().lower()
    return v in {"1", "true", "yes", "on"}


def _parse_int(val: str | None, name: str, default: int) -> int:
    if val is None or not val.strip():
        return default
    try:
        return int(val.strip())
    except ValueError as err:
        raise ValueError(f"Invalid integer for {name}: '{val}'") from err


def get_settings(env_dict: dict[str, str] | None = None) -> Settings:
    """Load and validate settings from environment variables (or provided dict)."""
    env = os.environ if env_dict is None else env_dict

    env_val = env.get("CARECAST_ENV", "prod")
    db_path = env.get("CARECAST_DB_PATH", "data/carecast.db")
    enable_docs = _parse_bool(env.get("CARECAST_ENABLE_DOCS"), default=False)
    rate_get = _parse_int(env.get("CARECAST_RATE_GET_PER_MIN"), "CARECAST_RATE_GET_PER_MIN", 60)
    rate_post = _parse_int(env.get("CARECAST_RATE_POST_PER_MIN"), "CARECAST_RATE_POST_PER_MIN", 20)
    trusted_proxy = _parse_bool(env.get("CARECAST_TRUSTED_PROXY"), default=False)
    hsts = _parse_bool(env.get("CARECAST_HSTS"), default=False)
    log_level = env.get("CARECAST_LOG_LEVEL", "INFO")

    return Settings(
        env=env_val,
        db_path=db_path,
        enable_docs=enable_docs,
        rate_get_per_min=rate_get,
        rate_post_per_min=rate_post,
        trusted_proxy=trusted_proxy,
        hsts=hsts,
        log_level=log_level,
    )


def load_toml(path: Path | str) -> dict[str, Any]:
    """Load and parse a TOML file using stdlib tomllib.
    
    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If TOML syntax is invalid.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    try:
        with open(file_path, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as err:
        raise ValueError(f"Failed to parse TOML in {file_path}: {err}") from err
