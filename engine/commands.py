"""Command registry — the CLI's table of subcommands.

Each :class:`Command` declares its name, help, how to configure its argparse
subparser, and how to run it against the wired :class:`Engine`. ``build_parser``
and dispatch in :mod:`__main__` iterate this table, so adding a subcommand is a
single entry here — mirroring the drop-in manager registry, rather than edits
spread across the parser, a dispatch ladder, and a handler.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .domain import KNOWN_PLATFORMS, LATEST, Tool
from .managers import Registry

if TYPE_CHECKING:
    from .services import Engine


@dataclass(frozen=True)
class Command:
    """One CLI subcommand: how to declare it and how to run it."""

    name: str
    help: str
    configure: Callable[[argparse.ArgumentParser], None]
    run: Callable[[Engine, argparse.Namespace], int]
    needs_engine: bool = True  # completion needs neither engine nor manifest
    needs_manifest: bool = True  # add creates the manifest, so it doesn't require one
    tool_arg: bool = False  # first positional is a tool name (drives completion)


def _add_common(parser: argparse.ArgumentParser, *, tags=True, yes=True, dry=True) -> None:
    if tags:
        parser.add_argument("--tags", help="comma-separated tags to filter (e.g. core,dev)")
    if yes:
        parser.add_argument("--yes", action="store_true", help="assume yes for all prompts")
    if dry:
        parser.add_argument(
            "--dry-run", action="store_true", help="show actions without changing anything"
        )


def _tags(value: str | None) -> set[str] | None:
    return {t.strip() for t in value.split(",") if t.strip()} if value else None


def _ok(outcome) -> int:
    return 0 if outcome.ok else 1


# ── per-command parser configuration ──────────────────────────────────


def _cfg_listing(p):
    # Shared by `list` and `status`: tag filter + JSON, no mutation flags.
    _add_common(p, yes=False, dry=False)
    p.add_argument("--json", action="store_true", help="emit JSON on stdout instead of a table")


def _cfg_update(p):
    _add_common(p, yes=False)


def _cfg_doctor(p):
    p.add_argument("--json", action="store_true", help="emit JSON on stdout")


def _cfg_add(p):
    _add_common(p, tags=False)
    p.add_argument("name")
    p.add_argument("--manager")
    p.add_argument("--package")
    p.add_argument("--version")
    p.add_argument("--platforms", help="comma-separated: macos,linux,wsl")
    p.add_argument("--add-tags", dest="tags", help="comma-separated tags")
    p.add_argument("--post-install", help="post-install health-check command")
    p.add_argument("--health-check", help="command `doctor` runs to verify health")
    p.add_argument("--install", action="store_true", help="install immediately after adding")


def _cfg_pin(p):
    _add_common(p, tags=False, yes=False, dry=False)
    p.add_argument("name")
    p.add_argument("version", nargs="?", help="version to pin (default: currently installed)")


def _cfg_config(p):
    p.add_argument("action", choices=["list", "get", "set", "unset"])
    p.add_argument("key", nargs="?", help="default_tags | default_platform")
    p.add_argument("value", nargs="?", help="value for `set`")


def _cfg_why(p):
    p.add_argument("name")
    p.add_argument("--json", action="store_true", help="emit JSON on stdout")


def _cfg_remove(p):
    _add_common(p, tags=False)
    p.add_argument("name")


def _cfg_unpin(p):
    _add_common(p, tags=False, yes=False, dry=False)
    p.add_argument("name")


def _cfg_export(p):
    p.add_argument("--write", action="store_true", help="merge discoveries into the manifest")


def _cfg_completion(p):
    p.add_argument("shell", choices=["bash", "zsh"])


# ── handlers ──────────────────────────────────────────────────────────


def _run_add(engine, args):
    console = engine.console
    known = Registry.known_names()
    manager, package = args.manager, args.package
    interactive = sys.stdin.isatty()
    if not manager and interactive:
        manager = input(f"manager {known}: ").strip()
    if not package and interactive:
        package = input(f"package [{args.name}]: ").strip() or args.name
    if not manager or not package:
        console.error("add requires --manager and --package (or an interactive terminal).")
        return 1
    if manager not in known:
        console.error(f"unknown manager '{manager}'. Known: {', '.join(known)}")
        return 1
    if args.install and manager == "script":
        console.error(
            "add --install can't provision a 'script' tool: it needs an `install` "
            "command that add does not capture. Add it without --install, define "
            f"[tools.{args.name}.options].install in software.toml, then run `zconfig sync`."
        )
        return 1
    tool = Tool(
        name=args.name,
        manager=manager,
        package=package,
        version=args.version or LATEST,
        platforms=tuple(args.platforms.split(",")) if args.platforms else KNOWN_PLATFORMS,
        tags=tuple(t for t in (args.tags or "").split(",") if t),
        post_install=args.post_install,
        health_check=args.health_check,
    )
    return _ok(engine.add(tool, install_now=args.install))


def _run_completion(_engine, args):
    from .completion import completion_script

    print(completion_script(args.shell), end="")
    return 0


COMMANDS: tuple[Command, ...] = (
    Command(
        "bootstrap",
        "install prerequisites then sync",
        _add_common,
        lambda e, a: _ok(e.bootstrap(_tags(a.tags), assume_yes=a.yes)),
    ),
    Command(
        "sync",
        "converge the machine to the manifest",
        _add_common,
        lambda e, a: _ok(e.sync(_tags(a.tags), assume_yes=a.yes)),
    ),
    Command(
        "list",
        "list declared tools (no live probing)",
        _cfg_listing,
        lambda e, a: _ok(e.list_tools(_tags(a.tags), as_json=a.json)),
    ),
    Command(
        "status",
        "show drift vs the manifest",
        _cfg_listing,
        lambda e, a: _ok(e.status(_tags(a.tags), as_json=a.json)),
    ),
    Command(
        "update",
        "interactively update outdated tools",
        _cfg_update,
        lambda e, a: _ok(e.update(_tags(a.tags))),
    ),
    Command("add", "add a tool to the manifest", _cfg_add, _run_add, needs_manifest=False),
    Command(
        "remove",
        "uninstall and drop a tool",
        _cfg_remove,
        lambda e, a: _ok(e.remove(a.name, assume_yes=a.yes)),
        tool_arg=True,
    ),
    Command(
        "pin",
        "pin a tool to a version",
        _cfg_pin,
        lambda e, a: _ok(e.pin(a.name, a.version)),
        tool_arg=True,
    ),
    Command(
        "unpin",
        "unpin a tool (track latest)",
        _cfg_unpin,
        lambda e, a: _ok(e.unpin(a.name)),
        tool_arg=True,
    ),
    Command(
        "doctor",
        "check environment health",
        _cfg_doctor,
        lambda e, a: _ok(e.doctor(as_json=a.json)),
    ),
    Command(
        "export",
        "snapshot installed software as manifest entries",
        _cfg_export,
        lambda e, a: _ok(e.export(write=a.write)),
    ),
    Command(
        "config",
        "view or edit the [settings] table",
        _cfg_config,
        lambda e, a: _ok(e.config(a.action, a.key, a.value)),
    ),
    Command(
        "why",
        "explain how a tool resolves and its live state",
        _cfg_why,
        lambda e, a: _ok(e.why(a.name, as_json=a.json)),
        tool_arg=True,
    ),
    Command(
        "completion",
        "print a shell completion script (bash|zsh)",
        _cfg_completion,
        _run_completion,
        needs_engine=False,
    ),
)

COMMANDS_BY_NAME: dict[str, Command] = {c.name: c for c in COMMANDS}


def command_names() -> list[str]:
    return [c.name for c in COMMANDS]


def tool_arg_command_names() -> list[str]:
    return [c.name for c in COMMANDS if c.tool_arg]
