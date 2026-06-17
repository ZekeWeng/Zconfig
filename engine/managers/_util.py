"""Small parsing helpers shared by manager adapters. Not an adapter itself —
the leading underscore keeps the discovery walk from importing it as one.
"""

from __future__ import annotations

import json as _json
import urllib.error
import urllib.request


def first_token(line: str) -> str:
    parts = line.split()
    return parts[0] if parts else ""


def nth_token(line: str, index: int) -> str | None:
    parts = line.split()
    return parts[index] if len(parts) > index else None


def clean_version(raw: str) -> str:
    return raw.strip().lstrip("v")


def pypi_latest(package: str, timeout: float = 5.0) -> str | None:
    """Latest version from the PyPI JSON API (stdlib urllib, no pip dep)."""
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = _json.loads(response.read().decode("utf-8"))
        return data["info"]["version"]
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        return None
