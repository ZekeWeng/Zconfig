"""Go adapter — binaries installed with ``go install pkg@version``.

The installed binary is named after the last path element of the package
(``github.com/x/lazygit`` -> ``lazygit``); override with options.binary when
that heuristic is wrong. Uninstall removes the binary from GOBIN/GOPATH/bin.
"""

from __future__ import annotations

import os

from ..domain import ResolvedTool
from ..ports import CommandResult, PackageManager
from . import register


@register
class GoManager(PackageManager):
    name = "go"

    def is_available(self) -> bool:
        return self.runner.which("go") is not None

    def _binary_name(self, tool: ResolvedTool) -> str:
        override = tool.options.get("binary")
        if override:
            return str(override)
        path = tool.package.split("@", 1)[0].rstrip("/")
        return path.split("/")[-1]

    def _gobin(self) -> str:
        result = self.runner.run(["go", "env", "GOBIN"], read_only=True)
        gobin = result.stdout.strip() if result.ok else ""
        if gobin:
            return gobin
        gopath = self.runner.run(["go", "env", "GOPATH"], read_only=True)
        root = gopath.stdout.strip() if gopath.ok else os.path.expanduser("~/go")
        return os.path.join(root, "bin")

    def is_installed(self, tool: ResolvedTool) -> bool:
        return self.runner.which(self._binary_name(tool)) is not None or os.path.exists(
            os.path.join(self._gobin(), self._binary_name(tool))
        )

    def installed_version(self, tool: ResolvedTool) -> str | None:
        binary = self.runner.which(self._binary_name(tool)) or os.path.join(
            self._gobin(), self._binary_name(tool)
        )
        result = self.runner.run(["go", "version", "-m", binary], read_only=True)
        if not result.ok:
            return None
        for line in result.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[0] == "mod":
                return fields[2].lstrip("v")
        return None

    def latest_version(self, tool: ResolvedTool) -> str | None:
        module = tool.package.split("@", 1)[0]
        result = self.runner.run(["go", "list", "-m", "-versions", module], read_only=True)
        if not result.ok or not result.stdout.strip():
            return None
        versions = result.stdout.split()[1:]
        return versions[-1].lstrip("v") if versions else None

    def _target(self, tool: ResolvedTool) -> str:
        base = tool.package.split("@", 1)[0]
        return f"{base}@{tool.version}" if tool.is_pinned else f"{base}@latest"

    def install(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run(["go", "install", self._target(tool)], capture=False)

    def update(self, tool: ResolvedTool) -> CommandResult:
        base = tool.package.split("@", 1)[0]
        return self.runner.run(["go", "install", f"{base}@latest"], capture=False)

    def uninstall(self, tool: ResolvedTool) -> CommandResult:
        target = os.path.join(self._gobin(), self._binary_name(tool))
        if os.path.exists(target):
            return self.runner.run(["rm", "-f", target])
        return CommandResult(0, "", "go binary not found; nothing to remove")

    def pin(self, tool: ResolvedTool) -> CommandResult:
        if tool.is_pinned:
            return self.runner.run(["go", "install", self._target(tool)], capture=False)
        return CommandResult(0, "", "go has no hold; pin enforced by manifest version")
