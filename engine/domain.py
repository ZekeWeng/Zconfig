"""Core domain — pure value objects and drift logic.

This module is the center of the hexagon: it imports nothing from the rest of
the engine and touches no OS, filesystem, network, or subprocess. Everything
here is deterministic given its inputs, which keeps the interesting decisions
(what to install, what is outdated, what is an orphan) trivially testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

# Canonical platform identifiers used throughout the manifest and engine.
MACOS = "macos"
LINUX = "linux"
WSL = "wsl"
KNOWN_PLATFORMS = (MACOS, LINUX, WSL)

LATEST = "latest"


class Status(str, Enum):
    """Where a tool stands relative to the manifest, for the current machine."""

    OK = "ok"  # installed, at the version we want
    MISSING = "missing"  # declared, not installed
    OUTDATED = "outdated"  # installed but a newer version is available (unpinned)
    PIN_DRIFT = "pin-drift"  # pinned to X, but a different version is installed
    PINNED = "pinned"  # pinned and satisfied — held, never auto-updated
    ORPHAN = "orphan"  # installed by zconfig, no longer in the manifest
    SKIPPED = "skipped"  # not applicable to this platform
    UNKNOWN = "unknown"  # manager unavailable, cannot determine


@dataclass(frozen=True, slots=True)
class Tool:
    """A declared piece of software, exactly as written in the manifest.

    Per-platform overrides live in ``overrides`` keyed by platform id; resolving
    a tool for a platform folds the override onto the base fields. ``options``
    carries adapter-specific extras (e.g. brew ``cask``, script commands).
    """

    name: str
    manager: str
    package: str
    version: str = LATEST
    platforms: tuple[str, ...] = KNOWN_PLATFORMS
    tags: tuple[str, ...] = ()
    pre_install: str | None = None
    post_install: str | None = None
    options: dict[str, object] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    overrides: dict[str, dict[str, object]] = field(default_factory=dict)

    @property
    def is_pinned(self) -> bool:
        return self.version != LATEST

    def applies_to(self, platform: str) -> bool:
        return platform in self.platforms

    def resolve(self, platform: str) -> ResolvedTool | None:
        """Fold any per-platform override onto the base fields.

        Returns ``None`` when the tool does not target ``platform`` — callers
        treat that as a skip rather than an error.
        """
        if not self.applies_to(platform):
            return None
        over = self.overrides.get(platform, {})
        return ResolvedTool(
            name=self.name,
            manager=str(over.get("manager", self.manager)),
            package=str(over.get("package", self.package)),
            version=str(over.get("version", self.version)),
            tags=self.tags,
            pre_install=_opt_str(over.get("pre_install", self.pre_install)),
            post_install=_opt_str(over.get("post_install", self.post_install)),
            options={**self.options, **over.get("options", {})},
            env={**self.env, **over.get("env", {})},
        )


@dataclass(frozen=True, slots=True)
class ResolvedTool:
    """A tool reduced to concrete fields for one platform — what adapters act on."""

    name: str
    manager: str
    package: str
    version: str
    tags: tuple[str, ...]
    pre_install: str | None
    post_install: str | None
    options: dict[str, object]
    env: dict[str, str] = field(default_factory=dict)

    @property
    def is_pinned(self) -> bool:
        return self.version != LATEST


@dataclass(frozen=True, slots=True)
class Settings:
    """Engine defaults declared in the manifest's ``[settings]`` table.

    Everything here is overridable per-invocation by a CLI flag or environment
    variable; these are just the persistent defaults a user bakes into the repo.
    """

    default_tags: tuple[str, ...] = ()
    default_platform: str | None = None


@dataclass(frozen=True, slots=True)
class Manifest:
    """The declared desired state — the whole ``software.toml`` as domain types."""

    tools: tuple[Tool, ...]
    settings: Settings = Settings()

    def get(self, name: str) -> Tool | None:
        return next((t for t in self.tools if t.name == name), None)

    def names(self) -> set[str]:
        return {t.name for t in self.tools}

    def for_platform(self, platform: str) -> tuple[ResolvedTool, ...]:
        resolved = (t.resolve(platform) for t in self.tools)
        return tuple(r for r in resolved if r is not None)

    def with_tool(self, tool: Tool) -> Manifest:
        kept = tuple(t for t in self.tools if t.name != tool.name)
        return Manifest(tools=kept + (tool,), settings=self.settings)

    def without_tool(self, name: str) -> Manifest:
        return Manifest(tools=tuple(t for t in self.tools if t.name != name), settings=self.settings)


@dataclass(frozen=True, slots=True)
class LockEntry:
    """A record that zconfig — not the user by hand — installed this tool.

    ``options`` carries the adapter extras needed to *remove* the tool later
    (notably the script adapter's ``uninstall`` command), so orphan cleanup
    stays possible after the tool is gone from the manifest.
    """

    name: str
    manager: str
    package: str
    version: str
    installed_at: str
    pinned: bool = False
    options: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Lock:
    entries: tuple[LockEntry, ...] = ()

    def get(self, name: str) -> LockEntry | None:
        return next((e for e in self.entries if e.name == name), None)

    def names(self) -> set[str]:
        return {e.name for e in self.entries}

    def upsert(self, entry: LockEntry) -> Lock:
        kept = tuple(e for e in self.entries if e.name != entry.name)
        return Lock(entries=kept + (entry,))

    def remove(self, name: str) -> Lock:
        return Lock(entries=tuple(e for e in self.entries if e.name != name))


@dataclass(frozen=True, slots=True)
class Observation:
    """What an adapter reports about a tool's actual state on this machine."""

    installed: bool
    current: str | None = None
    latest: str | None = None
    manager_available: bool = True


@dataclass(frozen=True, slots=True)
class Assessment:
    """A tool paired with its computed status — the unit a plan is built from."""

    name: str
    manager: str
    package: str
    desired_version: str
    status: Status
    current: str | None = None
    latest: str | None = None
    pinned: bool = False

    @property
    def needs_action(self) -> bool:
        return self.status in (Status.MISSING, Status.OUTDATED, Status.PIN_DRIFT, Status.ORPHAN)


def assess(tool: ResolvedTool, obs: Observation, locked: bool) -> Assessment:
    """Classify a declared tool against what's actually installed. Pure.

    ``locked`` says whether zconfig recorded installing it — only relevant for
    reporting; orphan detection (declared-gone-but-locked) is handled separately
    in :func:`find_orphans` because it needs the manifest/lock sets, not a tool.
    """
    base = dict(
        name=tool.name,
        manager=tool.manager,
        package=tool.package,
        desired_version=tool.version,
        current=obs.current,
        latest=obs.latest,
        pinned=tool.is_pinned,
    )
    if not obs.manager_available:
        return Assessment(status=Status.UNKNOWN, **base)
    if not obs.installed:
        return Assessment(status=Status.MISSING, **base)
    if tool.is_pinned:
        # A pin is satisfied only when the installed version matches exactly.
        if obs.current is not None and not _version_matches(obs.current, tool.version):
            return Assessment(status=Status.PIN_DRIFT, **base)
        return Assessment(status=Status.PINNED, **base)
    if obs.latest is not None and obs.current is not None and obs.current != obs.latest:
        return Assessment(status=Status.OUTDATED, **base)
    return Assessment(status=Status.OK, **base)


def find_orphans(manifest: Manifest, lock: Lock) -> tuple[LockEntry, ...]:
    """Tools zconfig installed that the manifest no longer declares.

    These are the only things sync may remove — software the user installed by
    hand is never in the lock, so it is never a removal candidate.
    """
    declared = manifest.names()
    return tuple(e for e in lock.entries if e.name not in declared)


def validate_manifest(manifest: Manifest, known_managers: set[str]) -> list[str]:
    """Static checks over a manifest. Pure — ``known_managers`` is passed in so
    the domain stays unaware of the adapter registry. Returns one human-readable
    problem string per issue (empty list = clean), for fail-fast at the boundary.
    """
    problems: list[str] = []
    for t in manifest.tools:
        for plat in t.platforms:
            if plat not in KNOWN_PLATFORMS:
                problems.append(f"{t.name}: unknown platform '{plat}' (known: {', '.join(KNOWN_PLATFORMS)})")
        for plat in t.overrides:
            if plat not in KNOWN_PLATFORMS:
                problems.append(f"{t.name}: override targets unknown platform '{plat}'")
        # Check the effective manager/options for every platform the tool targets.
        for plat in t.platforms:
            if plat not in KNOWN_PLATFORMS:
                continue
            resolved = t.resolve(plat)
            if resolved is None:
                continue
            if resolved.manager not in known_managers:
                problems.append(f"{t.name} ({plat}): unknown manager '{resolved.manager}'")
            if resolved.manager == "script" and not resolved.options.get("install"):
                problems.append(f"{t.name} ({plat}): script manager needs an options.install command")
    return problems


def _version_matches(installed: str, pinned: str) -> bool:
    # Tolerate a leading "v" and prefix pins (pinning "1.2" matches "1.2.3").
    a = installed.lstrip("v")
    b = pinned.lstrip("v")
    return a == b or a.startswith(b + ".")


def _opt_str(value: object) -> str | None:
    return None if value is None else str(value)


def replace_tool_version(tool: Tool, version: str) -> Tool:
    """Return a copy of ``tool`` pinned/unpinned to ``version`` (pure helper)."""
    return replace(tool, version=version)
