"""Console adapter — colored status lines, aligned tables, interactive prompts.

Implements the Console port. Colors are dropped when stdout is not a TTY (pipes,
CI logs) so captured output stays clean. Every line is also mirrored to an
optional log sink for the persistent run log.
"""

from __future__ import annotations

import sys
from typing import Callable

_RED = "\033[0;31m"
_GREEN = "\033[0;32m"
_YELLOW = "\033[1;33m"
_DIM = "\033[2m"
_NC = "\033[0m"


class TerminalConsole:
    def __init__(self, *, log: Callable[[str], None] | None = None, assume_yes: bool = False) -> None:
        self._log = log or (lambda _msg: None)
        self._assume_yes = assume_yes
        self._color = sys.stdout.isatty()

    def _paint(self, color: str, message: str) -> str:
        return f"{color}{message}{_NC}" if self._color else message

    def _emit(self, color: str, message: str) -> None:
        print(self._paint(color, message))
        self._log(message)

    def info(self, message: str) -> None:
        self._emit(_YELLOW, message)

    def ok(self, message: str) -> None:
        self._emit(_GREEN, message)

    def warn(self, message: str) -> None:
        self._emit(_YELLOW, message)

    def error(self, message: str) -> None:
        print(self._paint(_RED, message), file=sys.stderr)
        self._log("ERROR: " + message)

    def table(self, headers: list[str], rows: list[list[str]]) -> None:
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))
        header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
        print(self._paint(_YELLOW, header_line))
        print(self._paint(_DIM, "  ".join("-" * widths[i] for i in range(len(headers)))))
        for row in rows:
            print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
        for line in (header_line, *("  ".join(row) for row in rows)):
            self._log(line)

    def confirm(self, prompt: str, *, default: bool = False) -> bool:
        if self._assume_yes:
            return True
        suffix = " [Y/n] " if default else " [y/N] "
        if not sys.stdin.isatty():
            # Non-interactive and no --yes: refuse destructive actions safely.
            return default
        answer = input(self._paint(_YELLOW, prompt + suffix)).strip().lower()
        if not answer:
            return default
        return answer in ("y", "yes")

    def choose(self, prompt: str, choices: dict[str, str], default: str) -> str:
        if self._assume_yes or not sys.stdin.isatty():
            return default
        menu = " ".join(f"[{k}]{label}" for k, label in choices.items())
        answer = input(self._paint(_YELLOW, f"{prompt} {menu}: ")).strip().lower()
        return answer if answer in choices else default
