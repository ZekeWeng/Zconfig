"""Atomic text writes for the manifest and lockfile.

Both are sources of truth, and ``Path.write_text`` truncates before writing —
a crash or full disk mid-write would leave a half-written, unparseable file.
Writing to a temp file on the same directory and ``os.replace``-ing it in makes
the swap atomic: readers see either the old file or the complete new one.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)  # atomic on POSIX and Windows when same filesystem
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise
