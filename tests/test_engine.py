"""Engine tests — stdlib unittest only (no pip dependency, runs anywhere).

Focus is the pure domain (the interesting decisions) plus the IO round-trips
that have bitten us before: TOML quoting of non-bare keys, control-char
escaping, nested override sub-tables, and lock options for orphan removal.
"""

from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
from pathlib import Path

from engine.domain import (
    Lock,
    LockEntry,
    Manifest,
    Observation,
    Settings,
    Status,
    Tool,
    assess,
    find_orphans,
    validate_manifest,
)
from engine.lockfile import JsonLockStore
from engine.ports import CommandResult, CommandRunner
from engine.shell import DryRunner
from engine.toml_io import TomlManifestStore


def tool(**kw) -> Tool:
    base = dict(name="rg", manager="brew", package="ripgrep")
    base.update(kw)
    return Tool(**base)


class ResolveTests(unittest.TestCase):
    def test_platform_filter_returns_none(self):
        self.assertIsNone(tool(platforms=("linux",)).resolve("macos"))

    def test_override_folds_manager_package_and_env(self):
        t = tool(
            platforms=("macos", "linux"),
            env={"A": "1"},
            overrides={"linux": {"manager": "apt", "package": "rg-bin", "env": {"B": "2"}}},
        )
        mac = t.resolve("macos")
        lin = t.resolve("linux")
        self.assertEqual((mac.manager, mac.package, mac.env), ("brew", "ripgrep", {"A": "1"}))
        self.assertEqual(lin.manager, "apt")
        self.assertEqual(lin.package, "rg-bin")
        self.assertEqual(lin.env, {"A": "1", "B": "2"})  # base + override merge


class AssessTests(unittest.TestCase):
    def setUp(self):
        self.t = tool().resolve("macos")
        self.pinned = tool(version="14.1.0").resolve("macos")

    def test_missing(self):
        a = assess(self.t, Observation(installed=False), locked=False)
        self.assertEqual(a.status, Status.MISSING)

    def test_ok_when_current_equals_latest(self):
        a = assess(self.t, Observation(installed=True, current="14.1.0", latest="14.1.0"), locked=True)
        self.assertEqual(a.status, Status.OK)

    def test_outdated(self):
        a = assess(self.t, Observation(installed=True, current="14.0.0", latest="14.1.0"), locked=True)
        self.assertEqual(a.status, Status.OUTDATED)

    def test_pinned_satisfied(self):
        a = assess(self.pinned, Observation(installed=True, current="14.1.0"), locked=True)
        self.assertEqual(a.status, Status.PINNED)

    def test_pin_drift(self):
        a = assess(self.pinned, Observation(installed=True, current="15.0.0"), locked=True)
        self.assertEqual(a.status, Status.PIN_DRIFT)

    def test_pin_prefix_match_is_satisfied(self):
        t = tool(version="14.1").resolve("macos")
        a = assess(t, Observation(installed=True, current="14.1.3"), locked=True)
        self.assertEqual(a.status, Status.PINNED)

    def test_unknown_when_manager_unavailable(self):
        a = assess(self.t, Observation(installed=False, manager_available=False), locked=False)
        self.assertEqual(a.status, Status.UNKNOWN)


class OrphanTests(unittest.TestCase):
    def test_locked_but_undeclared_is_orphan(self):
        manifest = Manifest(tools=(tool(name="keep"),))
        lock = Lock(
            entries=(
                LockEntry("keep", "brew", "keep", "1", "t"),
                LockEntry("gone", "brew", "gone", "1", "t"),
            )
        )
        orphans = find_orphans(manifest, lock)
        self.assertEqual([o.name for o in orphans], ["gone"])

    def test_manifest_mutations_preserve_settings(self):
        m = Manifest(tools=(tool(name="a"),), settings=Settings(default_tags=("core",)))
        self.assertEqual(m.with_tool(tool(name="b")).settings.default_tags, ("core",))
        self.assertEqual(m.without_tool("a").settings.default_tags, ("core",))


class TomlRoundTripTests(unittest.TestCase):
    def _round_trip(self, manifest: Manifest) -> Manifest:
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(manifest)
        with path.open("rb") as handle:
            tomllib.load(handle)  # must be valid TOML
        return TomlManifestStore(path).load()

    def test_non_bare_key_is_quoted(self):
        m = Manifest(tools=(tool(name="node@22", package="node@22"),))
        self.assertIn("node@22", self._round_trip(m).names())

    def test_control_chars_escaped_and_preserved(self):
        nasty = 'a"\\\nb\tc\x01d'
        out = self._round_trip(Manifest(tools=(tool(name="x", package=nasty),)))
        self.assertEqual(out.get("x").package, nasty)

    def test_nested_override_options_and_env(self):
        m = Manifest(
            tools=(
                tool(
                    name="t",
                    options={"cask": True},
                    env={"E": "1"},
                    overrides={"linux": {"manager": "script", "options": {"check": "x"}, "env": {"F": "2"}}},
                ),
            )
        )
        out = self._round_trip(m).get("t")
        self.assertEqual(out.options, {"cask": True})
        self.assertEqual(out.env, {"E": "1"})
        self.assertEqual(out.overrides["linux"]["options"], {"check": "x"})
        self.assertEqual(out.overrides["linux"]["env"], {"F": "2"})

    def test_settings_round_trip(self):
        m = Manifest(tools=(tool(),), settings=Settings(default_tags=("core",), default_platform="linux"))
        out = self._round_trip(m)
        self.assertEqual(out.settings, Settings(default_tags=("core",), default_platform="linux"))


class LockRoundTripTests(unittest.TestCase):
    def test_options_persist_for_orphan_removal(self):
        path = Path(tempfile.mktemp(suffix=".lock"))
        store = JsonLockStore(path)
        store.save(Lock(entries=(LockEntry("t", "script", "t", "1", "now", options={"uninstall": "rm x"}),)))
        loaded = store.load().get("t")
        self.assertEqual(loaded.options, {"uninstall": "rm x"})

    def test_missing_file_is_empty_lock(self):
        self.assertEqual(JsonLockStore(Path(tempfile.mktemp())).load(), Lock())


class FakeRunner(CommandRunner):
    """Records mutating calls; answers a programmable map for read-only probes."""

    def __init__(self, probe_ok: bool = True):
        self.calls: list[list[str]] = []
        self.probe_ok = probe_ok

    def run(self, args, *, capture=True, read_only=False, env=None):
        self.calls.append(args)
        return CommandResult(code=0, stdout="", stderr="")

    def which(self, program):
        return "/usr/bin/" + program


class ValidateTests(unittest.TestCase):
    KNOWN = {"brew", "apt", "script"}

    def test_clean_manifest_has_no_problems(self):
        m = Manifest(tools=(tool(platforms=("macos",), tags=("core",)),))
        self.assertEqual(validate_manifest(m, self.KNOWN), [])

    def test_unknown_platform_flagged(self):
        m = Manifest(tools=(tool(platforms=("plan9",)),))
        self.assertTrue(any("plan9" in p for p in validate_manifest(m, self.KNOWN)))

    def test_unknown_manager_flagged(self):
        m = Manifest(tools=(tool(manager="nosuch", platforms=("macos",)),))
        self.assertTrue(any("unknown manager" in p for p in validate_manifest(m, self.KNOWN)))

    def test_script_without_install_flagged(self):
        m = Manifest(tools=(tool(manager="script", platforms=("macos",)),))
        self.assertTrue(any("install command" in p for p in validate_manifest(m, self.KNOWN)))


class AtomicWriteTests(unittest.TestCase):
    def test_creates_and_overwrites(self):
        from engine.atomic import write_text_atomic

        path = Path(tempfile.mkdtemp()) / "f.txt"
        write_text_atomic(path, "one")
        self.assertEqual(path.read_text(), "one")
        write_text_atomic(path, "two")
        self.assertEqual(path.read_text(), "two")
        # no leftover temp files in the directory
        self.assertEqual([p.name for p in path.parent.iterdir()], ["f.txt"])


class _SilentConsole:
    def info(self, m): ...
    def ok(self, m): ...
    def warn(self, m): ...
    def error(self, m): ...
    def table(self, headers, rows, *, highlight=None): ...
    def confirm(self, prompt, *, default=False): return default
    def choose(self, prompt, choices, default): return default


class _NoManagers:
    def get(self, name): return None
    def all(self): return []


class _FixedClock:
    def now_iso(self): return "2026-01-01T00:00:00+00:00"


class ConfigCommandTests(unittest.TestCase):
    def _engine(self, manifest_path: Path):
        from engine.services import Engine

        return Engine(
            manifest_store=TomlManifestStore(manifest_path),
            lock_store=JsonLockStore(Path(tempfile.mktemp())),
            managers=_NoManagers(),
            runner=FakeRunner(),
            console=_SilentConsole(),
            clock=_FixedClock(),
            platform="macos",
        )

    def test_set_unset_round_trip(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(Manifest(tools=(tool(),)))
        engine = self._engine(path)

        engine.config("set", "default_tags", "core,dev")
        self.assertEqual(TomlManifestStore(path).load().settings.default_tags, ("core", "dev"))

        engine.config("unset", "default_tags")
        self.assertEqual(TomlManifestStore(path).load().settings.default_tags, ())

    def test_set_rejects_unknown_platform(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(Manifest(tools=(tool(),)))
        outcome = self._engine(path).config("set", "default_platform", "freebsd")
        self.assertFalse(outcome.ok)


class JsonOutputTests(unittest.TestCase):
    def _engine(self, manifest_path: Path):
        from engine.services import Engine

        return Engine(
            manifest_store=TomlManifestStore(manifest_path),
            lock_store=JsonLockStore(Path(tempfile.mktemp())),
            managers=_NoManagers(),
            runner=FakeRunner(),
            console=_SilentConsole(),
            clock=_FixedClock(),
            platform="macos",
        )

    def _capture(self, fn) -> str:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            fn()
        return buffer.getvalue()

    def test_status_json_is_pure_and_parseable(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(Manifest(tools=(tool(name="a", platforms=("macos",)),)))
        engine = self._engine(path)
        out = self._capture(lambda: engine.status(as_json=True))
        data = json.loads(out)  # stdout must be valid JSON, nothing else
        self.assertEqual(data[0]["name"], "a")
        self.assertIn("status", data[0])

    def test_why_json_structure(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(Manifest(tools=(tool(name="a", platforms=("macos",)),)))
        engine = self._engine(path)
        out = self._capture(lambda: engine.why("a", as_json=True))
        report = json.loads(out)
        self.assertTrue(report["targeted"])
        self.assertEqual(report["resolved"]["manager"], "brew")
        self.assertFalse(report["lock"]["installed_by_zconfig"])

    def test_list_json_and_tag_filter(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(
            Manifest(tools=(tool(name="a", tags=("core",)), tool(name="b", tags=("dev",))))
        )
        engine = self._engine(path)
        every = json.loads(self._capture(lambda: engine.list_tools(as_json=True)))
        self.assertEqual({t["name"] for t in every}, {"a", "b"})
        core = json.loads(self._capture(lambda: engine.list_tools({"core"}, as_json=True)))
        self.assertEqual([t["name"] for t in core], ["a"])


class DryRunnerTests(unittest.TestCase):
    def test_dryrun_suppresses_mutation_runs_probe(self):
        logged: list[str] = []
        inner = FakeRunner()
        dry = DryRunner(inner, sink=logged.append)
        dry.run(["brew", "install", "x"])  # mutation
        dry.run(["brew", "list"], read_only=True)  # probe
        self.assertEqual(inner.calls, [["brew", "list"]])  # only the probe reached the inner runner
        self.assertEqual(len(logged), 1)
        self.assertIn("would run", logged[0])


if __name__ == "__main__":
    unittest.main()
