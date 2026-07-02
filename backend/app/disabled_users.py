from __future__ import annotations

import json
import threading
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DISABLED_FILE = _DATA_DIR / "disabled_users.json"
_lock = threading.Lock()


def _load() -> set[str]:
    if not _DISABLED_FILE.exists():
        return set()
    try:
        return set(json.loads(_DISABLED_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()


def _save(emails: set[str]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _DISABLED_FILE.write_text(
        json.dumps(sorted(emails), ensure_ascii=True),
        encoding="utf-8",
    )


def is_disabled(email: str) -> bool:
    with _lock:
        return email in _load()


def disable_user(email: str) -> None:
    with _lock:
        disabled = _load()
        disabled.add(email)
        _save(disabled)


def enable_user(email: str) -> None:
    with _lock:
        disabled = _load()
        disabled.discard(email)
        _save(disabled)


def list_disabled() -> list[str]:
    with _lock:
        return sorted(_load())
