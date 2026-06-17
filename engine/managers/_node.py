"""Shared base for node global-package adapters (npm, pnpm).

Underscore-prefixed so discovery skips it. npm and pnpm differ only in the CLI
name and a couple of subcommand spellings, so they parameterize this base rather
than importing each other (adapters must not depend on sibling adapters).
"""

from __future__ import annotations

import json

from ..domain import ResolvedTool
from ..ports import CommandResult, PackageManager


class NodeGlobalManager(PackageManager):
    cli: str = ""  # "npm" | "pnpm"

    def is_available(self) -> bool:
        return self.runner.which(self.cli) is not None

    def is_installed(self, tool: ResolvedTool) -> bool:
        return self.installed_version(tool) is not None

    def installed_version(self, tool: ResolvedTool) -> str | None:
        result = self.runner.run([self.cli, "ls", "-g", "--depth=0", "--json"], read_only=True)
        if not result.ok:
            return None
        try:
            data = json.loads(result.stdout or "{}")
            dep = data.get("dependencies", {}).get(tool.package)
            return dep.get("version") if dep else None
        except json.JSONDecodeError:
            return None

    def latest_version(self, tool: ResolvedTool) -> str | None:
        result = self.runner.run([self.cli, "view", tool.package, "version"], read_only=True)
        return result.stdout.strip() or None if result.ok else None

    def _target(self, tool: ResolvedTool) -> str:
        return f"{tool.package}@{tool.version}" if tool.is_pinned else f"{tool.package}@latest"

    def install(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run([self.cli, "install", "-g", self._target(tool)], capture=False)

    def update(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run([self.cli, "install", "-g", f"{tool.package}@latest"], capture=False)

    def uninstall(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run([self.cli, "uninstall", "-g", tool.package], capture=False)

    def pin(self, tool: ResolvedTool) -> CommandResult:
        if tool.is_pinned:
            return self.runner.run([self.cli, "install", "-g", self._target(tool)], capture=False)
        return CommandResult(0, "", "npm/pnpm have no hold; pin enforced by manifest version")
