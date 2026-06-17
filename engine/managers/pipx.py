"""pipx adapter — isolated Python application installs.

Latest-version lookup uses the PyPI JSON API over stdlib urllib (no pip dep);
it returns None offline, which simply renders the tool as ``ok`` rather than
erroring. A pin installs ``package==version``.
"""

from __future__ import annotations

import json

from ..domain import ResolvedTool
from ..ports import CommandResult, PackageManager
from . import register
from ._util import pypi_latest


@register
class PipxManager(PackageManager):
    name = "pipx"

    def is_available(self) -> bool:
        return self.runner.which("pipx") is not None

    def _metadata(self, package: str) -> dict | None:
        result = self.runner.run(["pipx", "list", "--json"], read_only=True)
        if not result.ok:
            return None
        try:
            data = json.loads(result.stdout or "{}")
        except json.JSONDecodeError:
            return None
        venv = data.get("venvs", {}).get(package)
        return venv.get("metadata", {}).get("main_package") if venv else None

    def is_installed(self, tool: ResolvedTool) -> bool:
        return self._metadata(tool.package) is not None

    def installed_version(self, tool: ResolvedTool) -> str | None:
        meta = self._metadata(tool.package)
        return meta.get("package_version") if meta else None

    def latest_version(self, tool: ResolvedTool) -> str | None:
        return pypi_latest(tool.package)

    def install(self, tool: ResolvedTool) -> CommandResult:
        target = f"{tool.package}=={tool.version}" if tool.is_pinned else tool.package
        return self.runner.run(["pipx", "install", target], capture=False)

    def update(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run(["pipx", "upgrade", tool.package], capture=False)

    def uninstall(self, tool: ResolvedTool) -> CommandResult:
        return self.runner.run(["pipx", "uninstall", tool.package], capture=False)

    def pin(self, tool: ResolvedTool) -> CommandResult:
        if tool.is_pinned:
            return self.runner.run(["pipx", "install", "--force", f"{tool.package}=={tool.version}"], capture=False)
        return CommandResult(0, "", "pipx has no hold; pin enforced by manifest version")
