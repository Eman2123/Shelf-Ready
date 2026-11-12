"""Load untracked env files into os.environ (never overriding values already set).

Looked up in this order: backend/.env, <repo>/.env, <repo>/.env.local. Real environment variables
(Render, Vercel, your shell) always win, so deployed hosts need no file at all.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = (ROOT / "backend" / ".env", ROOT / ".env", ROOT / ".env.local")


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if value[:1] in ("'", '"') and value.endswith(value[:1]) and len(value) >= 2:
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()  # trailing comment on an unquoted value
        if key.strip():
            values[key.strip()] = value
    return values


def load_env(files: Iterable[Path] = ENV_FILES) -> list[str]:
    """Returns the names of the variables it set (never their values)."""
    loaded: list[str] = []
    for path in files:
        if not path.is_file():
            continue
        for key, value in parse_env(path.read_text(encoding="utf-8-sig")).items():
            if value != "" and not os.environ.get(key):
                os.environ[key] = value
                loaded.append(key)
    return loaded


load_env()
