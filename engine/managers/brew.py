"""Homebrew adapter.

Delegates to the ``brew`` CLI rather than reimplementing it — the existing
Brewfile and pinned installers stay authoritative for *how* brew installs; this
adapter is the manifest's window onto them. Brew has no concept of installing an
arbitrary historical version, so a pin maps to ``brew pin`` (hold at current),
and the manifest version field is treated as the held version.
"""

from __future__ import annotations

import json

from ..domain import ResolvedTool
from ..ports import CommandResult, CommandRunner, PackageManager
from . import register

# Suppress brew's implicit `brew update` (a network round-trip) on every read.
# Status reflects locally-known state; an explicit `brew update` still refreshes.
_NO_AUTO_UPDATE = {"HOMEBREW_NO_AUTO_UPDATE": "1"}


@register
class BrewManager(PackageManager):
    name = "brew"
    # Homebrew installs only the current formula version; a pin maps to `brew pin`
    # (hold current), so pinning to a *different* version can never converge.
    installs_exact_version = False

    def __init__(self, runner: CommandRunner) -> None:
        super().__init__(runner)
        # All caches are populated once per run from batched calls — a full
        # manifest costs three brew invocations, not three per tool.
        self._formulae: dict[str, str] | None = None
        self._casks: dict[str, str] | None = None
        self._outdated: dict[str, str | None] | None = None

    def _is_cask(self, tool: ResolvedTool) -> bool:
        return bool(tool.options.get("cask"))

    def is_available(self) -> bool:
        return self.runner.which("brew") is not None

    def _installed_map(self, *, cask: bool) -> dict[str, str]:
        """name -> installed version for every formula (or cask), from one call."""
        cache = self._casks if cask else self._formulae
        if cache is None:
            cache = {}
            cmd = ["brew", "list", "--versions"] + (["--cask"] if cask else ["--formula"])
            result = self.runner.run(cmd, read_only=True, env=_NO_AUTO_UPDATE)
            if result.ok:
                for line in result.stdout.splitlines():
                    parts = line.split()
                    if len(parts) >= 2:
                        cache[parts[0]] = parts[-1]  # highest of possibly several versions
            if cask:
                self._casks = cache
            else:
                self._formulae = cache
        return cache

    def is_installed(self, tool: ResolvedTool) -> bool:
        return tool.package in self._installed_map(cask=self._is_cask(tool))

    def installed_version(self, tool: ResolvedTool) -> str | None:
        return self._installed_map(cask=self._is_cask(tool)).get(tool.package)

    def _outdated_map(self) -> dict[str, str | None]:
        """name -> available version for everything behind, from one call.

        ``brew outdated --json=v2`` answers the whole manifest at once. ``--greedy``
        is intentionally omitted: auto-updating casks keep themselves current, so
        probing their appcasts would be slow and report drift the user can't act on.
        """
        if self._outdated is None:
            self._outdated = {}
            result = self.runner.run(
                ["brew", "outdated", "--json=v2"], read_only=True, env=_NO_AUTO_UPDATE
            )
            if result.ok:
                try:
                    data = json.loads(result.stdout or "{}")
                    for entry in data.get("formulae", []) + data.get("casks", []):
                        self._outdated[entry["name"]] = entry.get("current_version")
                except (json.JSONDecodeError, KeyError):
                    pass
        return self._outdated

    def latest_version(self, tool: ResolvedTool) -> str | None:
        outdated = self._outdated_map()
        if tool.package in outdated:
            return outdated[tool.package]
        # Not in the outdated set means it's current: latest == what's installed.
        return self.installed_version(tool)

    def _invalidate(self) -> None:
        """Drop the per-run probe caches after a mutation.

        The maps snapshot brew's state once and reuse it all run. Without this,
        sync's post-install ``is_installed`` check (services.py) reads the
        pre-install snapshot and reports a just-installed tool as still missing.
        """
        self._formulae = None
        self._casks = None
        self._outdated = None

    def install(self, tool: ResolvedTool) -> CommandResult:
        cmd = ["brew", "install"]
        if self._is_cask(tool):
            cmd.append("--cask")
        cmd.append(tool.package)
        result = self.runner.run(cmd, capture=False)
        self._invalidate()
        return result

    def update(self, tool: ResolvedTool) -> CommandResult:
        cmd = ["brew", "upgrade"]
        if self._is_cask(tool):
            cmd.append("--cask")
        cmd.append(tool.package)
        result = self.runner.run(cmd, capture=False)
        self._invalidate()
        return result

    def uninstall(self, tool: ResolvedTool) -> CommandResult:
        cmd = ["brew", "uninstall"]
        if self._is_cask(tool):
            cmd.append("--cask")
        cmd.append(tool.package)
        result = self.runner.run(cmd, capture=False)
        self._invalidate()
        return result

    def pin(self, tool: ResolvedTool) -> CommandResult:
        if self._is_cask(tool):
            return CommandResult(0, "", "brew cannot pin casks; manifest pin still honored")
        return self.runner.run(["brew", "pin", tool.package])

    def export_installed(self) -> list[dict[str, object]]:
        if not self.is_available():
            return []
        out: list[dict[str, object]] = []
        leaves = self.runner.run(["brew", "leaves"], read_only=True)
        if leaves.ok:
            for pkg in leaves.stdout.split():
                out.append({"name": pkg, "manager": "brew", "package": pkg, "tags": ["exported"]})
        casks = self.runner.run(["brew", "list", "--cask"], read_only=True)
        if casks.ok:
            for pkg in casks.stdout.split():
                out.append(
                    {
                        "name": pkg,
                        "manager": "brew",
                        "package": pkg,
                        "tags": ["exported"],
                        "options": {"cask": True},
                    }
                )
        return out
