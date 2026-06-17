"""Lockfile adapter — JSON record of what zconfig installed.

JSON, not TOML, because the stdlib round-trips it losslessly and the lock is
machine state, not something a human hand-edits. Its only job is to make
removal and orphan detection safe: a tool is a removal candidate only if it is
in here, which means zconfig put it there — never the user by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

from .domain import Lock, LockEntry
from .ports import LockStore

_VERSION = 1


class JsonLockStore(LockStore):
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Lock:
        if not self.path.exists():
            return Lock()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return Lock()
        entries = tuple(
            LockEntry(
                name=name,
                manager=str(body.get("manager", "")),
                package=str(body.get("package", name)),
                version=str(body.get("version", "")),
                installed_at=str(body.get("installed_at", "")),
                pinned=bool(body.get("pinned", False)),
                options=dict(body.get("options", {})),
            )
            for name, body in sorted(data.get("tools", {}).items())
        )
        return Lock(entries=entries)

    def save(self, lock: Lock) -> None:
        payload = {
            "version": _VERSION,
            "tools": {
                entry.name: {
                    "manager": entry.manager,
                    "package": entry.package,
                    "version": entry.version,
                    "installed_at": entry.installed_at,
                    "pinned": entry.pinned,
                    **({"options": entry.options} if entry.options else {}),
                }
                for entry in sorted(lock.entries, key=lambda e: e.name)
            },
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
