"""Composition root + CLI adapter.

This is the only module that knows about every concrete adapter at once: it
parses arguments, opens the log, wires the ports to their implementations, and
dispatches to the application layer. Keep wiring here — not in services.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .console import TerminalConsole
from .domain import KNOWN_PLATFORMS, LATEST, Tool
from .lockfile import JsonLockStore
from .managers import Registry
from .platform import SystemClock, detect_platform
from .services import Engine
from .shell import DryRunner, SystemRunner
from .toml_io import TomlManifestStore


def _zconfig_dir() -> Path:
    return Path(os.environ.get("ZCONFIG_DIR", str(Path.home() / ".zconfig")))


class _FileLog:
    """Append-only run log. Returns a sink callable mirroring console output."""

    def __init__(self, path: Path, command: str) -> None:
        self.path = path
        try:
            self.handle = path.open("a", encoding="utf-8")
            self.handle.write(f"\n=== zconfig {command} @ {SystemClock().now_iso()} ===\n")
        except OSError:
            self.handle = None

    def write(self, message: str) -> None:
        if self.handle:
            self.handle.write(message + "\n")
            self.handle.flush()


def _build_engine(args: argparse.Namespace) -> Engine:
    root = _zconfig_dir()
    os.environ.setdefault("ZCONFIG_DIR", str(root))
    manifest_path = Path(args.manifest) if args.manifest else root / "software.toml"
    lock_path = Path(args.lock) if args.lock else root / "zconfig.lock"
    log_path = Path(args.log_file) if args.log_file else root / ".zconfig.log"

    logger = _FileLog(log_path, args.command)
    console = TerminalConsole(log=logger.write, assume_yes=getattr(args, "yes", False))

    runner = SystemRunner()
    if getattr(args, "dry_run", False):
        runner = DryRunner(runner, sink=console.info)

    manifest_store = TomlManifestStore(manifest_path)
    return Engine(
        manifest_store=manifest_store,
        lock_store=JsonLockStore(lock_path),
        managers=Registry(runner),
        runner=runner,
        console=console,
        clock=SystemClock(),
        platform=_resolve_platform(manifest_store),
        dry_run=getattr(args, "dry_run", False),
    )


def _resolve_platform(store: TomlManifestStore) -> str:
    """Precedence: $ZCONFIG_PLATFORM > manifest [settings].default_platform >
    auto-detected. Lets a Mac plan a Linux converge, or pin a host explicitly."""
    override = os.environ.get("ZCONFIG_PLATFORM")
    if override:
        return override
    if store.exists():
        try:
            configured = store.load().settings.default_platform
            if configured:
                return configured
        except (OSError, ValueError):
            pass
    return detect_platform()


def _tags(value: str | None) -> set[str] | None:
    return {t.strip() for t in value.split(",") if t.strip()} if value else None


def _require_manifest(engine: Engine, console: TerminalConsole) -> bool:
    if not engine.manifest_store.exists():
        console.error(f"No manifest found at {engine.manifest_store.path}. Create software.toml first.")
        return False
    return True


def _cmd_add(engine: Engine, args: argparse.Namespace) -> int:
    console = engine.console
    manager = args.manager
    package = args.package
    interactive = sys.stdin.isatty()
    if not manager and interactive:
        manager = input(f"manager {Registry.known_names()}: ").strip()
    if not package and interactive:
        package = input(f"package [{args.name}]: ").strip() or args.name
    if not manager or not package:
        console.error("add requires --manager and --package (or an interactive terminal).")
        return 1
    if manager not in Registry.known_names():
        console.error(f"unknown manager '{manager}'. Known: {', '.join(Registry.known_names())}")
        return 1
    tool = Tool(
        name=args.name,
        manager=manager,
        package=package,
        version=args.version or LATEST,
        platforms=tuple(args.platforms.split(",")) if args.platforms else KNOWN_PLATFORMS,
        tags=tuple(t for t in (args.tags or "").split(",") if t),
        post_install=args.post_install,
    )
    return 0 if engine.add(tool, install_now=args.install).ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zconfig", description="Declarative software management.")
    parser.add_argument("--version", action="version", version=f"zconfig {__version__}")
    parser.add_argument("--manifest", help="path to software.toml (default: $ZCONFIG_DIR/software.toml)")
    parser.add_argument("--lock", help="path to zconfig.lock (default: $ZCONFIG_DIR/zconfig.lock)")
    parser.add_argument("--log-file", help="path to the run log (default: $ZCONFIG_DIR/.zconfig.log)")
    sub = parser.add_subparsers(dest="command", required=True)

    def with_common(p, *, tags=True, yes=True, dry=True):
        if tags:
            p.add_argument("--tags", help="comma-separated tags to filter (e.g. core,dev)")
        if yes:
            p.add_argument("--yes", action="store_true", help="assume yes for all prompts")
        if dry:
            p.add_argument("--dry-run", action="store_true", help="show actions without changing anything")
        return p

    with_common(sub.add_parser("bootstrap", help="install prerequisites then sync"))
    with_common(sub.add_parser("sync", help="converge the machine to the manifest"))
    with_common(sub.add_parser("status", help="show drift vs the manifest"), yes=False, dry=False)
    with_common(sub.add_parser("update", help="interactively update outdated tools"), yes=False)
    with_common(sub.add_parser("doctor", help="check environment health"), tags=False, yes=False, dry=False)

    p_add = with_common(sub.add_parser("add", help="add a tool to the manifest"), tags=False)
    p_add.add_argument("name")
    p_add.add_argument("--manager")
    p_add.add_argument("--package")
    p_add.add_argument("--version")
    p_add.add_argument("--platforms", help="comma-separated: macos,linux,wsl")
    p_add.add_argument("--add-tags", dest="tags", help="comma-separated tags")
    p_add.add_argument("--post-install", help="post-install health-check command")
    p_add.add_argument("--install", action="store_true", help="install immediately after adding")

    p_remove = with_common(sub.add_parser("remove", help="uninstall and drop a tool"), tags=False)
    p_remove.add_argument("name")

    p_pin = with_common(sub.add_parser("pin", help="pin a tool to a version"), tags=False, yes=False, dry=False)
    p_pin.add_argument("name")
    p_pin.add_argument("version", nargs="?", help="version to pin (default: currently installed)")

    p_unpin = with_common(sub.add_parser("unpin", help="unpin a tool (track latest)"), tags=False, yes=False, dry=False)
    p_unpin.add_argument("name")

    p_export = with_common(sub.add_parser("export", help="snapshot installed software as manifest entries"), tags=False, yes=False, dry=False)
    p_export.add_argument("--write", action="store_true", help="merge discoveries into the manifest")

    p_config = sub.add_parser("config", help="view or edit the [settings] table")
    p_config.add_argument("action", choices=["list", "get", "set", "unset"])
    p_config.add_argument("key", nargs="?", help="default_tags | default_platform")
    p_config.add_argument("value", nargs="?", help="value for `set`")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    engine = _build_engine(args)
    console = engine.console

    if args.command == "add":
        return _cmd_add(engine, args)

    # Every other command reads the manifest first.
    if not _require_manifest(engine, console):
        return 1

    if args.command == "status":
        return 0 if engine.status(_tags(args.tags)).ok else 1
    if args.command == "sync":
        return 0 if engine.sync(_tags(args.tags), assume_yes=args.yes).ok else 1
    if args.command == "bootstrap":
        return 0 if engine.bootstrap(_tags(args.tags), assume_yes=args.yes).ok else 1
    if args.command == "update":
        return 0 if engine.update(_tags(args.tags)).ok else 1
    if args.command == "remove":
        return 0 if engine.remove(args.name, assume_yes=args.yes).ok else 1
    if args.command == "pin":
        return 0 if engine.pin(args.name, args.version).ok else 1
    if args.command == "unpin":
        return 0 if engine.unpin(args.name).ok else 1
    if args.command == "doctor":
        return 0 if engine.doctor().ok else 1
    if args.command == "export":
        return 0 if engine.export(write=args.write).ok else 1
    if args.command == "config":
        return 0 if engine.config(args.action, args.key, args.value).ok else 1
    console.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
