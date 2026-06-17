"""Debian/Ubuntu apt adapter.

Install/remove need root; commands are prefixed with ``sudo`` unless already
root. A pin maps to ``apt-mark hold`` (the apt-native way to stop a package
from being upgraded), and an exact manifest version installs ``pkg=version``.
"""

from __future__ import annotations

import os

from ..domain import ResolvedTool
from ..ports import CommandResult, PackageManager
from . import register


def _sudo(args: list[str]) -> list[str]:
    return args if os.geteuid() == 0 else ["sudo", *args]


@register
class AptManager(PackageManager):
    name = "apt"

    def is_available(self) -> bool:
        return self.runner.which("apt-get") is not None

    def is_installed(self, tool: ResolvedTool) -> bool:
        return self.runner.run(["dpkg", "-s", tool.package], read_only=True).ok

    def installed_version(self, tool: ResolvedTool) -> str | None:
        result = self.runner.run(["dpkg-query", "-W", "-f=${Version}", tool.package], read_only=True)
        return result.stdout.strip() or None if result.ok else None

    def latest_version(self, tool: ResolvedTool) -> str | None:
        result = self.runner.run(["apt-cache", "policy", tool.package], read_only=True)
        if not result.ok:
            return None
        for line in result.stdout.splitlines():
            if "Candidate:" in line:
                candidate = line.split("Candidate:", 1)[1].strip()
                return candidate if candidate and candidate != "(none)" else None
        return None

    def install(self, tool: ResolvedTool) -> CommandResult:
        target = f"{tool.package}={tool.version}" if tool.is_pinned else tool.package
        return self.runner.run(_sudo(["apt-get", "install", "-y", "--no-install-recommends", target]), capture=False)

    def update(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run(_sudo(["apt-get", "install", "--only-upgrade", "-y", tool.package]), capture=False)

    def uninstall(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run(_sudo(["apt-get", "remove", "-y", tool.package]), capture=False)

    def pin(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run(_sudo(["apt-mark", "hold", tool.package]))
