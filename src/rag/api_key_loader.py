# -*- coding: utf-8 -*-
"""API key loading helpers for RAG scripts.

Lookup priority:
1. .streamlit/secrets.toml
2. data/.env
3. repository-root .env

Secret values are never printed by this module.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

_PLACEHOLDER_VALUES = {"TODO", "TBD", "REPLACE_ME", "CHANGEME"}


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().strip('"').strip("'")
    if not normalized:
        return True
    return (
        normalized.startswith("<")
        or normalized.startswith("your_")
        or normalized.upper() in _PLACEHOLDER_VALUES
    )


def _load_from_secrets_toml(key: str) -> str | None:
    secrets_path = PROJECT_ROOT / ".streamlit" / "secrets.toml"
    if not secrets_path.exists():
        return None

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        with secrets_path.open("rb") as f:
            secret_data = tomllib.load(f)
    except Exception:
        return None

    secret_value = secret_data.get(key)
    if secret_value and not _is_placeholder(str(secret_value)):
        return str(secret_value)
    return None


def _load_from_env_files(key: str) -> str | None:
    for env_path in (PROJECT_ROOT / "data" / ".env", PROJECT_ROOT / ".env"):
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)

    env_value = os.getenv(key)
    if env_value and not _is_placeholder(env_value):
        return env_value
    return None


def load_api_key(key: str = "OPENAI_API_KEY") -> str:
    """Load an API key from secrets.toml first, then .env files."""

    api_key = _load_from_secrets_toml(key) or _load_from_env_files(key)
    if not api_key:
        raise ValueError(
            f"{key}가 설정되지 않음. .streamlit/secrets.toml 또는 .env를 확인하세요."
        )
    return api_key
