"""Platform & clock adapters — detect the host OS/arch; provide wall-clock time.

Kept out of the domain because both read the live environment. The rest of the
engine receives the detected platform string and never calls os.uname itself.
"""

from __future__ import annotations

import datetime
import platform as _platform

from .domain import LINUX, MACOS, WSL
from .ports import Clock


def detect_platform() -> str:
    system = _platform.system()
    if system == "Darwin":
        return MACOS
    if system == "Linux":
        # WSL exposes "microsoft" in the kernel release string.
        release = _platform.uname().release.lower()
        if "microsoft" in release or "wsl" in release:
            return WSL
        return LINUX
    return system.lower()


class SystemClock(Clock):
    def now_iso(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
