"""Platform & clock adapters — detect the host OS/arch; provide wall-clock time.

Kept out of the domain because both read the live environment. The rest of the
engine receives the detected platform string and never calls os.uname itself.
"""

from __future__ import annotations

import datetime
import os
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


def detect_arch() -> str:
    machine = _platform.machine().lower()
    return {"x86_64": "x86_64", "amd64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}.get(
        machine, machine
    )


def is_wsl() -> bool:
    return detect_platform() == WSL


def has_sudo_env() -> bool:
    return os.geteuid() == 0 or os.environ.get("ZCONFIG_ASSUME_SUDO") == "1"


class SystemClock(Clock):
    def now_iso(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
