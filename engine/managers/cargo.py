"""Rust cargo adapter — global crate binaries via ``cargo install``.

cargo has no hold mechanism, so a pin is enforced by installing the exact
``--version`` and never running the unpinned upgrade.
"""

from __future__ import annotations

from ..domain import ResolvedTool
from ..ports import CommandResult, PackageManager
from . import register


@register
class CargoManager(PackageManager):
    name = "cargo"

    def is_available(self) -> bool:
        return self.runner.which("cargo") is not None

    def _installed_line(self, package: str) -> str | None:
        result = self.runner.run(["cargo", "install", "--list"], read_only=True)
        if not result.ok:
            return None
        for line in result.stdout.splitlines():
            # Lines look like: "ripgrep v14.1.0:" (binaries indented beneath).
            if line and not line.startswith(" ") and line.split()[0] == package:
                return line
        return None

    def is_installed(self, tool: ResolvedTool) -> bool:
        return self._installed_line(tool.package) is not None

    def installed_version(self, tool: ResolvedTool) -> str | None:
        line = self._installed_line(tool.package)
        if not line:
            return None
        parts = line.split()  # "name vX.Y.Z:"
        version = parts[1] if len(parts) > 1 else None
        return version.lstrip("v").rstrip(":") if version else None

    def latest_version(self, tool: ResolvedTool) -> str | None:
        result = self.runner.run(["cargo", "search", tool.package, "--limit", "1"], read_only=True)
        if not result.ok:
            return None
        for line in result.stdout.splitlines():
            if line.startswith(f"{tool.package} ="):
                # `name = "1.2.3"    # description`
                return line.split('"')[1] if '"' in line else None
        return None

    def install(self, tool: ResolvedTool) -> CommandResult:
        cmd = ["cargo", "install", tool.package]
        if tool.is_pinned:
            cmd += ["--version", tool.version]
        return self.runner.run(cmd, capture=False)

    def update(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run(["cargo", "install", tool.package, "--force"], capture=False)

    def uninstall(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run(["cargo", "uninstall", tool.package], capture=False)

    def pin(self, tool: ResolvedTool) -> CommandResult:
        if tool.is_pinned:
            return self.runner.run(
                ["cargo", "install", tool.package, "--version", tool.version, "--force"],
                capture=False,
            )
        return CommandResult(0, "", "cargo has no hold; pin enforced by manifest version")
