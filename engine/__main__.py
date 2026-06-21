"""Composition root + CLI adapter.

This is the only module that knows about every concrete adapter at once: it
parses arguments, opens the log, wires the ports to their implementations, and
dispatches to the application layer. Keep wiring here — not in services.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import tomllib
from pathlib import Path

from . import __version__
from .commands import COMMANDS, COMMANDS_BY_NAME
from .console import TerminalConsole
from .lockfile import JsonLockStore
from .managers import Registry
from .platform import SystemClock, detect_platform
from .ports import Console
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
            # 0600: the log mirrors console output (including hook command
            # strings on failure, which may carry secrets) and is personal
            # machine state — no reason for group/other to read it.
            self.handle = path.open("a", encoding="utf-8")
            with contextlib.suppress(OSError):
                os.chmod(path, 0o600)
            self.handle.write(f"\n=== zconfig {command} @ {SystemClock().now_iso()} ===\n")
        except OSError:
            self.handle = None

    def write(self, message: str) -> None:
        if self.handle:
            self.handle.write(message + "\n")
            self.handle.flush()

    def close(self) -> None:
        if self.handle:
            with contextlib.suppress(OSError):
                self.handle.close()
            self.handle = None

    def __enter__(self) -> _FileLog:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _build_engine(args: argparse.Namespace) -> tuple[Engine, _FileLog]:
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
    engine = Engine(
        manifest_store=manifest_store,
        lock_store=JsonLockStore(lock_path),
        managers=Registry(runner),
        runner=runner,
        console=console,
        clock=SystemClock(),
        platform=_resolve_platform(manifest_store),
        dry_run=getattr(args, "dry_run", False),
    )
    return engine, logger


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


def _require_manifest(engine: Engine, console: Console) -> bool:
    if not engine.manifest_store.exists():
        # .path is a TomlManifestStore detail; the port stays filesystem-agnostic
        # and the composition root only ever wires that one concrete store.
        store_path = engine.manifest_store.path  # pyright: ignore[reportAttributeAccessIssue]
        console.error(f"No manifest found at {store_path}. Create software.toml first.")
        return False
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zconfig", description="Declarative software management.")
    parser.add_argument("--version", action="version", version=f"zconfig {__version__}")
    parser.add_argument(
        "--manifest", help="path to software.toml (default: $ZCONFIG_DIR/software.toml)"
    )
    parser.add_argument("--lock", help="path to zconfig.lock (default: $ZCONFIG_DIR/zconfig.lock)")
    parser.add_argument(
        "--log-file", help="path to the run log (default: $ZCONFIG_DIR/.zconfig.log)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for command in COMMANDS:
        command.configure(sub.add_parser(command.name, help=command.help))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = COMMANDS_BY_NAME[args.command]

    # completion needs no engine or manifest — print and exit. Its handler
    # ignores the engine arg, so passing None here is intentional.
    if not command.needs_engine:
        return command.run(None, args)  # pyright: ignore[reportArgumentType]

    engine, logger = _build_engine(args)
    console = engine.console
    try:
        if command.needs_manifest and not _require_manifest(engine, console):
            return 1
        return command.run(engine, args)
    except tomllib.TOMLDecodeError as exc:
        # A typo in software.toml is common — give a clear error, not a traceback.
        # .path is a TomlManifestStore detail (see _require_manifest).
        store_path = engine.manifest_store.path  # pyright: ignore[reportAttributeAccessIssue]
        console.error(f"{store_path}: invalid TOML — {exc}")
        return 1
    except OSError as exc:
        console.error(f"file error: {exc}")
        return 1
    finally:
        logger.close()


if __name__ == "__main__":
    sys.exit(main())
