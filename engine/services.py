"""Application layer — one method per subcommand, orchestrating the ports.

Depends only on domain types and port interfaces; never on a concrete adapter,
a package-manager binary, or the filesystem directly. The composition root
injects the concretes. Persistence (manifest/lock writes) and mutating commands
are guarded by ``dry_run`` so a read-only run never changes the machine.
"""

from __future__ import annotations

from dataclasses import dataclass

from .domain import (
    LATEST,
    Assessment,
    Lock,
    LockEntry,
    Manifest,
    ResolvedTool,
    Status,
    Tool,
    assess,
    find_orphans,
)
from .ports import Clock, CommandRunner, Console, LockStore, ManagerProvider, ManifestStore


@dataclass
class Outcome:
    ok: bool = True
    messages: tuple[str, ...] = ()


# Status value -> semantic color, so `status` reads at a glance.
_STATUS_COLORS = {
    Status.OK.value: "green",
    Status.PINNED.value: "green",
    Status.MISSING.value: "red",
    Status.PIN_DRIFT.value: "red",
    Status.ORPHAN.value: "red",
    Status.OUTDATED.value: "yellow",
    Status.UNKNOWN.value: "dim",
    Status.SKIPPED.value: "dim",
}


class Engine:
    def __init__(
        self,
        *,
        manifest_store: ManifestStore,
        lock_store: LockStore,
        managers: ManagerProvider,
        runner: CommandRunner,
        console: Console,
        clock: Clock,
        platform: str,
        dry_run: bool = False,
    ) -> None:
        self.manifest_store = manifest_store
        self.lock_store = lock_store
        self.managers = managers
        self.runner = runner
        self.console = console
        self.clock = clock
        self.platform = platform
        self.dry_run = dry_run

    # ── shared helpers ────────────────────────────────────────────────

    def _resolved(self, tags: set[str] | None) -> tuple[ResolvedTool, ...]:
        manifest = self.manifest_store.load()
        # No explicit --tags falls back to the manifest's default_tags (empty = all).
        if tags is None and manifest.settings.default_tags:
            tags = set(manifest.settings.default_tags)
        tools = manifest.for_platform(self.platform)
        if tags:
            tools = tuple(t for t in tools if tags & set(t.tags))
        return tools

    def _assess(self, tools: tuple[ResolvedTool, ...], lock: Lock) -> list[Assessment]:
        results = []
        for tool in tools:
            manager = self.managers.get(tool.manager)
            if manager is None:
                results.append(
                    Assessment(
                        name=tool.name,
                        manager=tool.manager,
                        package=tool.package,
                        desired_version=tool.version,
                        status=Status.UNKNOWN,
                    )
                )
                continue
            obs = manager.observe(tool)
            results.append(assess(tool, obs, lock.get(tool.name) is not None))
        return results

    def _run_hook(self, hook: str | None, name: str) -> bool:
        if not hook:
            return True
        if not self.runner.run(["bash", "-c", hook], capture=False).ok:
            self.console.error(f"  hook failed for {name}: {hook}")
            return False
        return True

    def _lock_entry(self, tool: ResolvedTool) -> LockEntry:
        manager = self.managers.get(tool.manager)
        version = (manager.installed_version(tool) if manager else None) or tool.version
        return LockEntry(
            name=tool.name,
            manager=tool.manager,
            package=tool.package,
            version=version,
            installed_at=self.clock.now_iso(),
            pinned=tool.is_pinned,
            options=dict(tool.options),
        )

    # ── status ────────────────────────────────────────────────────────

    def status(self, tags: set[str] | None = None) -> Outcome:
        manifest = self.manifest_store.load()
        lock = self.lock_store.load()
        tools = self._resolved(tags)
        results = self._assess(tools, lock)
        orphans = find_orphans(manifest, lock)

        rows = [
            [a.name, a.manager, a.status.value, a.current or "-", _want(a)]
            for a in sorted(results, key=lambda a: (a.status.value, a.name))
        ]
        for orphan in sorted(orphans, key=lambda e: e.name):
            rows.append([orphan.name, orphan.manager, Status.ORPHAN.value, orphan.version, "(remove)"])

        if not rows:
            self.console.info("No tools declared for this platform.")
            return Outcome()
        self.console.table(
            ["TOOL", "MANAGER", "STATUS", "CURRENT", "WANT"], rows, highlight=_STATUS_COLORS
        )
        self._print_drift_summary(results, orphans)
        return Outcome()

    def _print_drift_summary(self, results: list[Assessment], orphans) -> None:
        counts: dict[str, int] = {}
        for a in results:
            counts[a.status.value] = counts.get(a.status.value, 0) + 1
        parts = [f"{n} {status}" for status, n in sorted(counts.items())]
        if orphans:
            parts.append(f"{len(orphans)} orphan")
        self.console.info("Summary: " + ", ".join(parts))
        if counts.get(Status.OUTDATED.value):
            self.console.info("Run `zconfig update` to review outdated tools.")
        if counts.get(Status.MISSING.value) or counts.get(Status.PIN_DRIFT.value) or orphans:
            self.console.info("Run `zconfig sync` to converge to the manifest.")

    # ── sync ──────────────────────────────────────────────────────────

    def sync(self, tags: set[str] | None = None, *, assume_yes: bool = False) -> Outcome:
        manifest = self.manifest_store.load()
        lock = self.lock_store.load()
        tools = self._resolved(tags)
        results = self._assess(tools, lock)
        by_name = {t.name: t for t in tools}

        installed, failed, skipped, manual = 0, 0, 0, 0
        for a in results:
            if a.status in (Status.MISSING, Status.PIN_DRIFT):
                tool = by_name[a.name]
                manager = self.managers.get(tool.manager)
                if manager is not None and manager.name == "manual":
                    note = manager.install(tool).stderr.strip()
                    self.console.warn(f"  {a.name}: manual action required — {note}")
                    manual += 1
                elif self._provision(tool, action="install"):
                    lock = lock.upsert(self._lock_entry(tool))
                    installed += 1
                else:
                    failed += 1
            elif a.status == Status.UNKNOWN:
                self.console.warn(f"  {a.name}: manager '{a.manager}' unavailable — skipped")
                skipped += 1

        removed = self._remove_orphans(manifest, lock, assume_yes=assume_yes)
        lock = removed[1]
        self._save_lock(lock)

        outdated = sum(1 for a in results if a.status == Status.OUTDATED)
        parts = [f"{installed} installed", f"{removed[0]} removed", f"{failed} failed", f"{skipped} skipped"]
        if manual:
            parts.append(f"{manual} manual")
        self.console.ok("Sync complete: " + ", ".join(parts) + ".")
        if outdated:
            self.console.info(f"{outdated} tool(s) outdated — run `zconfig update`.")
        return Outcome(ok=failed == 0)

    def _provision(self, tool: ResolvedTool, *, action: str) -> bool:
        manager = self.managers.get(tool.manager)
        if manager is None:
            self.console.error(f"  {tool.name}: unknown manager '{tool.manager}'")
            return False
        if not manager.is_available():
            self.console.warn(f"  {tool.name}: manager '{tool.manager}' not available — skipped")
            return False

        verb = "Installing" if action == "install" else "Updating"
        self.console.info(f"{verb} {tool.name} ({tool.manager}:{tool.package})...")
        if not self._run_hook(tool.pre_install, tool.name):
            return False

        result = manager.install(tool) if action == "install" else manager.update(tool)
        if not result.ok:
            self.console.error(f"  {tool.name} failed: {result.stderr.strip() or result.code}")
            return False
        if result.stderr.strip():
            self.console.info(f"  note: {result.stderr.strip()}")

        if tool.is_pinned:
            manager.pin(tool)

        if self.dry_run:
            return True

        if not manager.is_installed(tool):
            self.console.error(f"  {tool.name}: install reported success but tool is still missing")
            return False
        if not self._run_hook(tool.post_install, tool.name):
            return False
        self.console.ok(f"  {tool.name} ok")
        return True

    def _remove_orphans(self, manifest: Manifest, lock: Lock, *, assume_yes: bool):
        orphans = find_orphans(manifest, lock)
        removed = 0
        for orphan in orphans:
            prompt = f"Remove orphaned {orphan.name} ({orphan.manager}:{orphan.package})?"
            if not (assume_yes or self.console.confirm(prompt, default=False)):
                self.console.info(f"  kept {orphan.name}")
                continue
            manager = self.managers.get(orphan.manager)
            tool = ResolvedTool(
                name=orphan.name,
                manager=orphan.manager,
                package=orphan.package,
                version=orphan.version,
                tags=(),
                pre_install=None,
                post_install=None,
                options=dict(orphan.options),
            )
            if manager and manager.is_available():
                result = manager.uninstall(tool)
                if not result.ok and not self.dry_run:
                    self.console.error(f"  {orphan.name}: uninstall failed: {result.stderr.strip()}")
                    continue
            lock = lock.remove(orphan.name)
            removed += 1
            self.console.ok(f"  removed {orphan.name}")
        return removed, lock

    # ── update (interactive) ──────────────────────────────────────────

    def update(self, tags: set[str] | None = None) -> Outcome:
        lock = self.lock_store.load()
        tools = self._resolved(tags)
        results = self._assess(tools, lock)
        by_name = {t.name: t for t in tools}
        outdated = [a for a in results if a.status == Status.OUTDATED]

        if not outdated:
            self.console.ok("Everything is up to date (pinned tools are held).")
            return Outcome()

        update_all = False
        manifest = self.manifest_store.load()
        for a in outdated:
            tool = by_name[a.name]
            label = f"{a.name}: {a.current or '?'} -> {a.latest or 'latest'}"
            choice = "u" if update_all else self.console.choose(
                f"Update {label}?",
                {"u": "pdate", "s": "kip", "p": "in current", "a": "ll"},
                default="s",
            )
            if choice == "a":
                update_all = True
                choice = "u"
            if choice == "u":
                if self._provision(tool, action="update"):
                    lock = lock.upsert(self._lock_entry(tool))
            elif choice == "p":
                pinned_version = a.current or LATEST
                manifest = manifest.with_tool(_pin_manifest_tool(manifest, a.name, pinned_version))
                self._save_manifest(manifest)
                manager = self.managers.get(tool.manager)
                if manager:
                    manager.pin(tool)
                existing = lock.get(a.name)
                lock = lock.upsert(
                    LockEntry(
                        a.name,
                        tool.manager,
                        tool.package,
                        pinned_version,
                        self.clock.now_iso(),
                        pinned=True,
                        options=existing.options if existing else dict(tool.options),
                    )
                )
                self.console.ok(f"  pinned {a.name} at {pinned_version}")
            else:
                self.console.info(f"  skipped {a.name}")
        self._save_lock(lock)
        return Outcome()

    # ── add / remove ──────────────────────────────────────────────────

    def add(self, tool: Tool, *, install_now: bool = False) -> Outcome:
        manifest = self.manifest_store.load()
        if manifest.get(tool.name):
            self.console.error(f"{tool.name} is already in the manifest.")
            return Outcome(ok=False)
        manifest = manifest.with_tool(tool)
        self._save_manifest(manifest)
        self.console.ok(f"Added {tool.name} to the manifest.")
        if install_now:
            resolved = tool.resolve(self.platform)
            if resolved is None:
                self.console.warn(f"{tool.name} does not target {self.platform}; not installing.")
            elif self._provision(resolved, action="install"):
                lock = self.lock_store.load().upsert(self._lock_entry(resolved))
                self._save_lock(lock)
        else:
            self.console.info("Run `zconfig sync` to install it.")
        return Outcome()

    def remove(self, name: str, *, assume_yes: bool = False) -> Outcome:
        manifest = self.manifest_store.load()
        tool = manifest.get(name)
        if tool is None:
            self.console.error(f"{name} is not in the manifest.")
            return Outcome(ok=False)
        resolved = tool.resolve(self.platform)
        if resolved is not None:
            manager = self.managers.get(resolved.manager)
            if manager and manager.is_available() and manager.is_installed(resolved):
                if assume_yes or self.console.confirm(
                    f"Uninstall {name} ({resolved.manager}:{resolved.package})?", default=False
                ):
                    result = manager.uninstall(resolved)
                    if result.ok or self.dry_run:
                        self.console.ok(f"  uninstalled {name}")
                    else:
                        self.console.error(f"  uninstall failed: {result.stderr.strip()}")
                else:
                    self.console.info(f"  left {name} installed")
        manifest = manifest.without_tool(name)
        self._save_manifest(manifest)
        lock = self.lock_store.load().remove(name)
        self._save_lock(lock)
        self.console.ok(f"Removed {name} from the manifest.")
        return Outcome()

    # ── pin / unpin ───────────────────────────────────────────────────

    def pin(self, name: str, version: str | None) -> Outcome:
        manifest = self.manifest_store.load()
        tool = manifest.get(name)
        if tool is None:
            self.console.error(f"{name} is not in the manifest.")
            return Outcome(ok=False)
        resolved = tool.resolve(self.platform)
        if version is None:
            manager = self.managers.get(resolved.manager) if resolved else None
            version = (manager.installed_version(resolved) if manager and resolved else None)
            if not version:
                self.console.error(f"Cannot detect an installed version of {name}; pass one explicitly.")
                return Outcome(ok=False)
        manifest = manifest.with_tool(_pin_manifest_tool(manifest, name, version))
        self._save_manifest(manifest)
        if resolved:
            manager = self.managers.get(resolved.manager)
            if manager and manager.is_available():
                manager.pin(resolved)
        lock = self.lock_store.load()
        entry = lock.get(name)
        if entry:
            self._save_lock(
                lock.upsert(
                    LockEntry(
                        entry.name,
                        entry.manager,
                        entry.package,
                        version,
                        entry.installed_at,
                        pinned=True,
                        options=entry.options,
                    )
                )
            )
        self.console.ok(f"Pinned {name} at {version}.")
        return Outcome()

    def unpin(self, name: str) -> Outcome:
        manifest = self.manifest_store.load()
        tool = manifest.get(name)
        if tool is None:
            self.console.error(f"{name} is not in the manifest.")
            return Outcome(ok=False)
        manifest = manifest.with_tool(_pin_manifest_tool(manifest, name, LATEST))
        self._save_manifest(manifest)
        self.console.ok(f"Unpinned {name} — it now tracks latest.")
        self.console.info("apt/brew holds are not auto-released; unhold manually if needed.")
        return Outcome()

    # ── doctor ────────────────────────────────────────────────────────

    def doctor(self) -> Outcome:
        problems = 0
        self.console.info("Package managers:")
        for manager in self.managers.all():
            mark = "ok " if manager.is_available() else "-- "
            self.console.info(f"  [{mark}] {manager.name}")

        manifest = self.manifest_store.load()
        lock = self.lock_store.load()
        tools = manifest.for_platform(self.platform)

        self.console.info("Declared tools on this platform:")
        for tool in tools:
            manager = self.managers.get(tool.manager)
            if manager is None:
                self.console.error(f"  {tool.name}: unknown manager '{tool.manager}'")
                problems += 1
                continue
            if not manager.is_available():
                self.console.warn(f"  {tool.name}: manager '{tool.manager}' not installed")
                continue
            if manager.is_installed(tool) and tool.post_install:
                if not self.runner.run(["bash", "-c", tool.post_install], read_only=True).ok:
                    self.console.error(f"  {tool.name}: health check failed ({tool.post_install})")
                    problems += 1

        orphans = find_orphans(manifest, lock)
        if orphans:
            self.console.warn(f"{len(orphans)} orphaned tool(s) in the lock: " + ", ".join(o.name for o in orphans))

        if problems:
            self.console.error(f"doctor found {problems} problem(s).")
            return Outcome(ok=False)
        self.console.ok("doctor: environment looks healthy.")
        return Outcome()

    # ── export ────────────────────────────────────────────────────────

    def export(self, *, write: bool = False) -> Outcome:
        discovered: list[Tool] = []
        for manager in self.managers.all():
            if not manager.is_available():
                continue
            for entry in manager.export_installed():
                discovered.append(
                    Tool(
                        name=str(entry["name"]),
                        manager=str(entry["manager"]),
                        package=str(entry.get("package", entry["name"])),
                        tags=tuple(entry.get("tags", ())),
                        options=dict(entry.get("options", {})),
                    )
                )
        if not discovered:
            self.console.warn("Nothing to export (no enumerable managers available).")
            return Outcome()

        if write:
            manifest = self.manifest_store.load() if self.manifest_store.exists() else Manifest(())
            existing = manifest.names()
            added = 0
            for tool in discovered:
                if tool.name not in existing:
                    manifest = manifest.with_tool(tool)
                    added += 1
            self._save_manifest(manifest)
            self.console.ok(f"Merged {added} new tool(s) into the manifest ({len(discovered) - added} already present).")
        else:
            from .toml_io import _render_tool  # render-only, no file write

            self.console.info(f"# {len(discovered)} installed tool(s) — review and merge as desired:")
            for tool in sorted(discovered, key=lambda t: t.name):
                print(_render_tool(tool))
        return Outcome()

    # ── bootstrap ─────────────────────────────────────────────────────

    def bootstrap(self, tags: set[str] | None = None, *, assume_yes: bool = False) -> Outcome:
        brew = self.managers.get("brew")
        if self.platform == "macos" and brew and not brew.is_available():
            self.console.error("Homebrew is required on macOS but was not found. Install it, then re-run.")
            return Outcome(ok=False)
        self.console.info("Bootstrap: converging machine to the manifest...")
        return self.sync(tags, assume_yes=assume_yes)

    # ── persistence guards ────────────────────────────────────────────

    def _save_manifest(self, manifest: Manifest) -> None:
        if self.dry_run:
            self.console.info("[dry-run] manifest not written")
            return
        self.manifest_store.save(manifest)

    def _save_lock(self, lock: Lock) -> None:
        if self.dry_run:
            return
        self.lock_store.save(lock)


def _want(a: Assessment) -> str:
    if a.pinned:
        return f"={a.desired_version}"
    return a.latest or a.desired_version


def _pin_manifest_tool(manifest: Manifest, name: str, version: str) -> Tool:
    from dataclasses import replace

    return replace(manifest.get(name), version=version)
