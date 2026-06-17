"""Ports — the interfaces that define how the application talks to the outside.

Depends only on domain types. Adapters (managers, TOML/JSON stores, the shell
runner, the console) implement these; the composition root wires concretes in.
Nothing here imports an adapter, a package-manager binary, or the filesystem.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .domain import Lock, Manifest, Observation, ResolvedTool


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.code == 0


class CommandRunner(ABC):
    """Runs external commands. The single seam where the engine touches a shell.

    Adapters receive a runner by injection rather than importing subprocess, so
    that one adapter never reaches into another and tests can pass a fake.
    """

    @abstractmethod
    def run(
        self,
        args: list[str],
        *,
        capture: bool = True,
        read_only: bool = False,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        """Run a command. ``read_only=True`` marks a probe that must execute even
        under ``--dry-run``; the default (mutating) is suppressed in dry-run."""

    @abstractmethod
    def which(self, program: str) -> str | None:
        ...


class PackageManager(ABC):
    """A backend adapter for one package manager.

    Concrete managers self-register (see ``managers/__init__.py``); adding one is
    a matter of dropping a file in that package — the core never edits.
    """

    name: str

    def __init__(self, runner: CommandRunner) -> None:
        self.runner = runner

    @abstractmethod
    def is_available(self) -> bool:
        """Is the manager itself usable on this machine?"""

    @abstractmethod
    def is_installed(self, tool: ResolvedTool) -> bool:
        ...

    @abstractmethod
    def installed_version(self, tool: ResolvedTool) -> str | None:
        ...

    @abstractmethod
    def latest_version(self, tool: ResolvedTool) -> str | None:
        ...

    @abstractmethod
    def install(self, tool: ResolvedTool) -> CommandResult:
        ...

    @abstractmethod
    def update(self, tool: ResolvedTool) -> CommandResult:
        ...

    @abstractmethod
    def uninstall(self, tool: ResolvedTool) -> CommandResult:
        ...

    @abstractmethod
    def pin(self, tool: ResolvedTool) -> CommandResult:
        """Best-effort hold the tool at ``tool.version`` so it won't drift."""

    def observe(self, tool: ResolvedTool) -> Observation:
        """Default probe: compose the cheap checks into one Observation."""
        if not self.is_available():
            return Observation(installed=False, manager_available=False)
        installed = self.is_installed(tool)
        current = self.installed_version(tool) if installed else None
        latest = self.latest_version(tool) if installed and not tool.is_pinned else None
        return Observation(installed=installed, current=current, latest=latest)

    def export_installed(self) -> list[dict[str, object]]:
        """Snapshot currently-installed packages as manifest-shaped dicts.

        Optional — managers that can enumerate their world override this; the
        default returns nothing so ``zconfig export`` simply skips them.
        """
        return []


class ManagerProvider(ABC):
    """Resolves a manager name to a ready-to-use adapter instance."""

    @abstractmethod
    def get(self, name: str) -> PackageManager | None:
        ...

    @abstractmethod
    def all(self) -> list[PackageManager]:
        ...


class ManifestStore(ABC):
    @abstractmethod
    def load(self) -> Manifest:
        ...

    @abstractmethod
    def save(self, manifest: Manifest) -> None:
        ...

    @abstractmethod
    def exists(self) -> bool:
        ...


class LockStore(ABC):
    @abstractmethod
    def load(self) -> Lock:
        ...

    @abstractmethod
    def save(self, lock: Lock) -> None:
        ...


class Console(ABC):
    """User-facing I/O: status lines, tables, prompts. The only place we print."""

    @abstractmethod
    def info(self, message: str) -> None:
        ...

    @abstractmethod
    def ok(self, message: str) -> None:
        ...

    @abstractmethod
    def warn(self, message: str) -> None:
        ...

    @abstractmethod
    def error(self, message: str) -> None:
        ...

    @abstractmethod
    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        ...

    @abstractmethod
    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        ...

    @abstractmethod
    def choose(self, prompt: str, choices: dict[str, str], default: str) -> str:
        """Single-key menu; ``choices`` maps key -> label. Returns the chosen key."""


class Clock(ABC):
    @abstractmethod
    def now_iso(self) -> str:
        ...
