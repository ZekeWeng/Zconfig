"""Shell adapter — the one module allowed to run subprocesses.

Implements the CommandRunner port. A ``--dry-run`` runner that passes probes
through (``read_only=True``) but suppresses mutations is provided so the whole
engine can be driven read-only without every call site checking a flag.
"""

from __future__ import annotations

import os
import shutil
import subprocess

from .ports import CommandResult, CommandRunner


class SystemRunner(CommandRunner):
    def run(self, args, *, capture=True, read_only=False, env=None) -> CommandResult:
        merged = {**os.environ, **(env or {})}
        try:
            completed = subprocess.run(
                args,
                capture_output=capture,
                text=True,
                env=merged,
                check=False,
            )
        except FileNotFoundError as exc:
            return CommandResult(code=127, stdout="", stderr=str(exc))
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

    def __init__(self, inner: CommandRunner, sink) -> None:
        self.inner = inner
        self.sink = sink

    def run(self, args, *, capture=True, read_only=False, env=None) -> CommandResult:
        if read_only:
            return self.inner.run(args, capture=capture, read_only=True, env=env)
        self.sink("[dry-run] would run: " + " ".join(args))
        return CommandResult(code=0, stdout="", stderr="")

    def which(self, program: str) -> str | None:
        return self.inner.which(program)
