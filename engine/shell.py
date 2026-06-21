"""Shell adapter — the one module allowed to run subprocesses.

Implements the CommandRunner port. A ``--dry-run`` runner that passes probes
through (``read_only=True``) but suppresses mutations is provided so the whole
engine can be driven read-only without every call site checking a flag.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable

from .ports import CommandResult, CommandRunner

# Read-only probes (version lookups, `brew list`, `npm view`, …) should answer
# quickly; cap them so a stalled network can't wedge `status`/`sync`. Mutations
# (installs) run unbounded — they can legitimately take many minutes.
_PROBE_TIMEOUT = 60.0


class SystemRunner(CommandRunner):
    def run(
        self,
        args: list[str],
        *,
        capture: bool = True,
        read_only: bool = False,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        merged = {**os.environ, **(env or {})}
        try:
            completed = subprocess.run(
                args,
                capture_output=capture,
                text=True,
                env=merged,
                check=False,
                timeout=_PROBE_TIMEOUT if read_only else None,
            )
        except FileNotFoundError as exc:
            return CommandResult(code=127, stdout="", stderr=str(exc))
        except subprocess.TimeoutExpired:
            return CommandResult(
                code=124,
                stdout="",
                stderr=f"timed out after {_PROBE_TIMEOUT:.0f}s: {' '.join(args)}",
            )
        return CommandResult(
            code=completed.returncode,
            stdout=(completed.stdout or "") if capture else "",
            stderr=(completed.stderr or "") if capture else "",
        )

    def which(self, program: str) -> str | None:
        return shutil.which(program)


class DryRunner(CommandRunner):
    """Wraps a real runner: read-only probes pass through, mutations are logged.

    ``read_only`` is declared by the caller (no guessing), so status/planning
    observe the real machine while every install/remove/upgrade becomes a printed
    no-op that reports success.
    """

    def __init__(self, inner: CommandRunner, sink: Callable[[str], None]) -> None:
        self.inner = inner
        self.sink = sink

    def run(
        self,
        args: list[str],
        *,
        capture: bool = True,
        read_only: bool = False,
        env: dict[str, str] | None = None,
    ) -> CommandResult:
        if read_only:
            return self.inner.run(args, capture=capture, read_only=True, env=env)
        self.sink("[dry-run] would run: " + " ".join(args))
        return CommandResult(code=0, stdout="", stderr="")

    def which(self, program: str) -> str | None:
        return self.inner.which(program)
