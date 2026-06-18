"""Small parsing helpers shared by manager adapters. Not an adapter itself —
the leading underscore keeps the discovery walk from importing it as one.
"""

from __future__ import annotations

import json as _json
import urllib.error
import urllib.parse
import urllib.request


def nth_token(line: str, index: int) -> str | None:
    parts = line.split()
    return parts[index] if len(parts) > index else None


def pypi_latest(package: str, timeout: float = 5.0) -> str | None:
    """Latest version from the PyPI JSON API (stdlib urllib, no pip dep).

    The package name is percent-encoded into the path so a name containing
    slashes or dot-segments cannot reshape the URL, and the request is built
    explicitly against https://pypi.org — defense in depth even though names
    come from the trusted manifest.
    """
    encoded = urllib.parse.quote(package, safe="")
    request = urllib.request.Request(
        f"https://pypi.org/pypi/{encoded}/json",
        headers={"Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = _json.loads(response.read().decode("utf-8"))
        return data["info"]["version"]
    except (urllib.error.URLError, KeyError, ValueError, TimeoutError):
        return None
