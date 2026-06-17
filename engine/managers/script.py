"""Generic script + manual adapters — the escape hatch and the coexist bridge.

``script`` runs shell snippets the tool declares under [tools.<name>.options]:
  check       command whose exit status means "installed" (default: command -v <package>)
  version     command printing the installed version (optional)
  latest      command printing the latest version (optional)
  install     command to install            (required)
  update      command to update             (default: re-run install)
  uninstall   command to remove             (optional)

Snippets run under ``bash -c`` with ZCONFIG_DIR exported, so a script tool can
delegate to the repo's existing installers — e.g. install = "run_installer vscode"
sourced from lib/bootstrap.sh — which is how the new manifest coexists with the
pinned per-tool installers without reimplementing them.

``manual`` is the same but never auto-installs: install() prints the instructions
in its ``install`` option and leaves the tool untouched for the user to handle.
"""

from __future__ import annotations

import shlex

from ..domain import ResolvedTool
from ..ports import CommandResult, PackageManager
from . import register


def _bash(cmd: str) -> list[str]:
    return ["bash", "-c", cmd]


@register
class ScriptManager(PackageManager):
    name = "script"

    def _opt(self, tool: ResolvedTool, key: str) -> str | None:
        value = tool.options.get(key)
        return str(value) if value else None

    def is_available(self) -> bool:
        return self.runner.which("bash") is not None

    def is_installed(self, tool: ResolvedTool) -> bool:
        # Quote the package in the auto-generated default check: a plain data
        # field must not become shell code (an explicit `check` option is the
        # documented place for intentional shell).
        check = self._opt(tool, "check") or f"command -v {shlex.quote(tool.package)}"
        return self.runner.run(_bash(check), read_only=True).ok

    def installed_version(self, tool: ResolvedTool) -> str | None:
        cmd = self._opt(tool, "version")
        if not cmd:
            return None
        result = self.runner.run(_bash(cmd), read_only=True)
        return result.stdout.strip().splitlines()[0] if result.ok and result.stdout.strip() else None

    def latest_version(self, tool: ResolvedTool) -> str | None:
        cmd = self._opt(tool, "latest")
        if not cmd:
            return None
        result = self.runner.run(_bash(cmd), read_only=True)
        return result.stdout.strip() or None if result.ok else None

    def install(self, tool: ResolvedTool) -> CommandResult:
        cmd = self._opt(tool, "install")
        if not cmd:
            return CommandResult(1, "", f"{tool.name}: script manager needs an `install` option")
        return self.runner.run(_bash(cmd), capture=False)

    def update(self, tool: ResolvedTool) -> CommandResult:
        cmd = self._opt(tool, "update") or self._opt(tool, "install")
        if not cmd:
            return CommandResult(1, "", f"{tool.name}: nothing to run for update")
        return self.runner.run(_bash(cmd), capture=False)

    def uninstall(self, tool: ResolvedTool) -> CommandResult:
        cmd = self._opt(tool, "uninstall")
        if not cmd:
            return CommandResult(1, "", f"{tool.name}: no `uninstall` option defined")
        return self.runner.run(_bash(cmd), capture=False)

    def pin(self, tool: ResolvedTool) -> CommandResult:
        return CommandResult(0, "", "script tools pin via the manifest version field")


@register
class ManualManager(ScriptManager):
    name = "manual"

    def install(self, tool: ResolvedTool) -> CommandResult:
        instructions = self._opt(tool, "install") or "see the tool's documentation"
        return CommandResult(0, "", f"manual step for {tool.name}: {instructions}")

    def update(self, tool: ResolvedTool) -> CommandResult:
        return self.install(tool)
