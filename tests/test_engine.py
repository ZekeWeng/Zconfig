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
    is_valid_tool_name,
    validate_manifest,
)
from engine.lockfile import JsonLockStore
from engine.ports import CommandResult, CommandRunner, PackageManager
from engine.shell import DryRunner
from engine.toml_io import TomlManifestStore


def tool(**kw) -> Tool:
    base = dict(name="rg", manager="brew", package="ripgrep")
    base.update(kw)
    return Tool(**base)


def _capture_stdout(fn) -> str:
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        fn()
    return buffer.getvalue()


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
        a = assess(self.t, Observation(installed=False))
        self.assertEqual(a.status, Status.MISSING)

    def test_ok_when_current_equals_latest(self):
        a = assess(self.t, Observation(installed=True, current="14.1.0", latest="14.1.0"))
        self.assertEqual(a.status, Status.OK)

    def test_outdated(self):
        a = assess(self.t, Observation(installed=True, current="14.0.0", latest="14.1.0"))
        self.assertEqual(a.status, Status.OUTDATED)

    def test_pinned_satisfied(self):
        a = assess(self.pinned, Observation(installed=True, current="14.1.0"))
        self.assertEqual(a.status, Status.PINNED)

    def test_pin_drift_when_manager_can_install_exact(self):
        a = assess(self.pinned, Observation(installed=True, current="15.0.0"))
        self.assertEqual(a.status, Status.PIN_DRIFT)

    def test_pin_unsatisfiable_when_manager_cannot_install_exact(self):
        # brew-style manager: a mismatched pin can never converge, so it must not
        # be reported as PIN_DRIFT (which would make sync reinstall every run).
        a = assess(
            self.pinned,
            Observation(installed=True, current="15.0.0"),
            pin_exact_supported=False,
        )
        self.assertEqual(a.status, Status.PIN_UNSATISFIABLE)

    def test_pinned_but_version_unreadable_is_unknown_not_pinned(self):
        # No installed version to compare against → can't claim the pin is satisfied.
        a = assess(self.pinned, Observation(installed=True, current=None))
        self.assertEqual(a.status, Status.UNKNOWN)

    def test_pin_prefix_match_is_satisfied(self):
        t = tool(version="14.1").resolve("macos")
        a = assess(t, Observation(installed=True, current="14.1.3"))
        self.assertEqual(a.status, Status.PINNED)

    def test_unknown_when_manager_unavailable(self):
        a = assess(self.t, Observation(installed=False, manager_available=False))
        self.assertEqual(a.status, Status.UNKNOWN)


class HealthCommandTests(unittest.TestCase):
    def test_explicit_health_check_wins_over_post_install(self):
        resolved = tool(post_install="rg --version", health_check="rg --count x README").resolve(
            "macos"
        )
        self.assertEqual(resolved.health_command, "rg --count x README")

    def test_falls_back_to_post_install(self):
        self.assertEqual(
            tool(post_install="rg --version").resolve("macos").health_command, "rg --version"
        )

    def test_none_when_neither_set(self):
        self.assertIsNone(tool().resolve("macos").health_command)

    def test_override_can_set_health_check_per_platform(self):
        t = tool(platforms=("macos", "linux"), overrides={"linux": {"health_check": "rg -V"}})
        self.assertIsNone(t.resolve("macos").health_command)
        self.assertEqual(t.resolve("linux").health_command, "rg -V")


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
                    overrides={
                        "linux": {"manager": "script", "options": {"check": "x"}, "env": {"F": "2"}}
                    },
                ),
            )
        )
        out = self._round_trip(m).get("t")
        self.assertEqual(out.options, {"cask": True})
        self.assertEqual(out.env, {"E": "1"})
        self.assertEqual(out.overrides["linux"]["options"], {"check": "x"})
        self.assertEqual(out.overrides["linux"]["env"], {"F": "2"})

    def test_health_check_round_trips(self):
        m = Manifest(tools=(tool(name="rg", health_check="rg --version"),))
        self.assertEqual(self._round_trip(m).get("rg").health_check, "rg --version")

    def test_settings_round_trip(self):
        m = Manifest(
            tools=(tool(),), settings=Settings(default_tags=("core",), default_platform="linux")
        )
        out = self._round_trip(m)
        self.assertEqual(out.settings, Settings(default_tags=("core",), default_platform="linux"))


class LockRoundTripTests(unittest.TestCase):
    def test_options_persist_for_orphan_removal(self):
        path = Path(tempfile.mktemp(suffix=".lock"))
        store = JsonLockStore(path)
        store.save(
            Lock(
                entries=(LockEntry("t", "script", "t", "1", "now", options={"uninstall": "rm x"}),)
            )
        )
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

    def test_tool_name_validation(self):
        for good in ("node@22", "font-x", "claude-code", "c++", "a.b"):
            self.assertTrue(is_valid_tool_name(good), good)
        for bad in ("", " ", "a b", "a\nb", "a\tb", "\x01"):
            self.assertFalse(is_valid_tool_name(bad), repr(bad))


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
    def confirm(self, prompt, *, default=False):
        return default

    def choose(self, prompt, choices, default):
        return default


class _NoManagers:
    def get(self, name):
        return None

    def all(self):
        return []


class _FixedClock:
    def now_iso(self):
        return "2026-01-01T00:00:00+00:00"


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

    def test_status_json_is_pure_and_parseable(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(Manifest(tools=(tool(name="a", platforms=("macos",)),)))
        engine = self._engine(path)
        out = _capture_stdout(lambda: engine.status(as_json=True))
        data = json.loads(out)  # stdout must be valid JSON, nothing else
        self.assertEqual(data[0]["name"], "a")
        self.assertIn("status", data[0])

    def test_why_json_structure(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(Manifest(tools=(tool(name="a", platforms=("macos",)),)))
        engine = self._engine(path)
        out = _capture_stdout(lambda: engine.why("a", as_json=True))
        report = json.loads(out)
        self.assertTrue(report["targeted"])
        self.assertEqual(report["resolved"]["manager"], "brew")
        self.assertFalse(report["lock"]["installed_by_zconfig"])

    def test_doctor_json_structure_and_ok_flag(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(Manifest(tools=(tool(manager="brew", platforms=("macos",)),)))
        engine = self._engine(path)  # _NoManagers => brew is unknown here
        report = json.loads(_capture_stdout(lambda: engine.doctor(as_json=True)))
        self.assertIn("managers", report)
        self.assertIn("ok", report)
        self.assertFalse(report["ok"])  # unknown manager is a manifest problem
        self.assertTrue(report["manifest_problems"])

    def test_list_json_and_tag_filter(self):
        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(
            Manifest(tools=(tool(name="a", tags=("core",)), tool(name="b", tags=("dev",))))
        )
        engine = self._engine(path)
        every = json.loads(_capture_stdout(lambda: engine.list_tools(as_json=True)))
        self.assertEqual({t["name"] for t in every}, {"a", "b"})
        core = json.loads(_capture_stdout(lambda: engine.list_tools({"core"}, as_json=True)))
        self.assertEqual([t["name"] for t in core], ["a"])


class CliBoundaryTests(unittest.TestCase):
    def test_malformed_toml_exits_clean_not_traceback(self):
        import contextlib
        import io

        from engine.__main__ import main

        path = Path(tempfile.mktemp(suffix=".toml"))
        path.write_text("[tools.broken\n")  # missing ]
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(
                [
                    "--manifest",
                    str(path),
                    "--lock",
                    tempfile.mktemp(),
                    "--log-file",
                    tempfile.mktemp(),  # isolate from the real ~/.zconfig log
                    "status",
                ]
            )
        self.assertEqual(code, 1)
        self.assertIn("invalid TOML", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())

    def test_log_file_is_private(self):
        import os
        import stat

        from engine.__main__ import _FileLog

        path = Path(tempfile.mktemp())
        with _FileLog(path, "test"):
            pass
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)


class ScriptSafetyTests(unittest.TestCase):
    def test_default_check_quotes_package_name(self):
        from engine.managers.script import ScriptManager

        runner = FakeRunner()
        evil = tool(
            name="evil",
            manager="script",
            package="x; touch /tmp/pwned",
            platforms=("macos",),
            options={"install": "true"},
        ).resolve("macos")
        ScriptManager(runner).is_installed(evil)
        # The generated check must shell-quote the package, not interpolate it raw.
        bash_cmd = runner.calls[0][2]
        self.assertIn("command -v 'x; touch /tmp/pwned'", bash_cmd)
        self.assertNotEqual(bash_cmd, "command -v x; touch /tmp/pwned")


class CompletionTests(unittest.TestCase):
    def test_bash_script_registers_and_completes_tool_args(self):
        from engine.completion import completion_script

        script = completion_script("bash")
        self.assertIn("complete -F _zconfig zconfig", script)
        self.assertIn("remove|pin|unpin|why", script)

    def test_zsh_script_has_compdef(self):
        from engine.completion import completion_script

        self.assertTrue(completion_script("zsh").startswith("#compdef zconfig"))

    def test_unknown_shell_is_none(self):
        from engine.completion import completion_script

        self.assertIsNone(completion_script("fish"))


class _StubManager(PackageManager):
    """A controllable manager: reports a fixed installed version and records installs."""

    def __init__(self, runner, *, name, installs_exact_version, current):
        super().__init__(runner)
        self.name = name
        self.installs_exact_version = installs_exact_version
        self._current = current
        self.installs: list[str] = []
        self.pinned_versions: list[str] = []

    def is_available(self):
        return True

    def is_installed(self, tool):
        return True

    def installed_version(self, tool):
        return self._current

    def latest_version(self, tool):
        return self._current

    def install(self, tool):
        self.installs.append(tool.name)
        return CommandResult(0, "", "")

    def update(self, tool):
        return CommandResult(0, "", "")

    def uninstall(self, tool):
        return CommandResult(0, "", "")

    def pin(self, tool):
        self.pinned_versions.append(tool.version)
        return CommandResult(0, "", "")


class _OneManager:
    def __init__(self, manager):
        self._manager = manager

    def get(self, name):
        return self._manager if name == self._manager.name else None

    def all(self):
        return [self._manager]


class BrewCacheTests(unittest.TestCase):
    """Regression: brew re-probes after a mutation, not trusting the per-run cache."""

    def test_is_installed_reflects_an_install_within_the_same_run(self):
        from engine.domain import ResolvedTool
        from engine.managers.brew import BrewManager

        class FlippingBrew(CommandRunner):
            """`brew list` reports ripgrep missing until `brew install` has run."""

            def __init__(self):
                self.installed = False

            def run(self, args, *, capture=True, read_only=False, env=None):
                if args[:2] == ["brew", "list"]:
                    return CommandResult(0, "ripgrep 14.1.0\n" if self.installed else "", "")
                if args[:2] == ["brew", "install"]:
                    self.installed = True
                    return CommandResult(0, "", "")
                return CommandResult(0, "", "")

            def which(self, program):
                return "/opt/homebrew/bin/brew"

        rg = ResolvedTool(
            name="rg",
            manager="brew",
            package="ripgrep",
            version="latest",
            tags=(),
            pre_install=None,
            post_install=None,
            options={},
        )
        manager = BrewManager(FlippingBrew())

        # arrange: assess probes is_installed first, snapshotting "missing"
        self.assertFalse(manager.is_installed(rg))
        # act: provision installs it (brew really lands it)
        manager.install(rg)
        # assert: the post-install verify must re-probe, not read the stale snapshot
        self.assertTrue(manager.is_installed(rg))


class VersionMatchTests(unittest.TestCase):
    """version_matches tolerates v-prefixes, apt epochs, Debian revisions, and +dfsg."""

    def test_plain_and_prefix_pins(self):
        from engine.domain import version_matches

        self.assertTrue(version_matches("1.2.3", "1.2.3"))
        self.assertTrue(version_matches("v1.2.3", "1.2.3"))
        self.assertTrue(version_matches("1.2.3", "1.2"))  # prefix pin
        self.assertFalse(version_matches("1.20.0", "1.2"))  # not a prefix

    def test_apt_epoch_and_revision(self):
        from engine.domain import version_matches

        # apt reports the full Debian version; a manifest pin is plain.
        self.assertTrue(version_matches("2:1.2.3-1ubuntu0", "1.2.3"))
        self.assertTrue(version_matches("1.2.3-1ubuntu0", "1.2.3"))
        self.assertTrue(version_matches("1.2.3+dfsg-1", "1.2.3"))  # repackaged upstream
        self.assertTrue(version_matches("2:1.2.3-1ubuntu0", "1.2"))
        self.assertFalse(version_matches("2:2.0.0", "1.2.3"))


class GoVersionTests(unittest.TestCase):
    """go latest_version returns the highest stable release, not the list's last
    element, and skips prereleases."""

    def test_latest_is_highest_stable_not_positional(self):
        from engine.domain import ResolvedTool
        from engine.managers.go import GoManager

        class FakeGo(CommandRunner):
            def run(self, args, *, capture=True, read_only=False, env=None):
                if args[:3] == ["go", "list", "-m"]:
                    # not ascending; the highest tag is a prerelease to be skipped
                    return CommandResult(0, "example.com/m v1.9.0 v1.10.0 v2.0.0-rc1\n", "")
                return CommandResult(0, "", "")

            def which(self, program):
                return "/usr/bin/go"

        tool = ResolvedTool(
            name="m",
            manager="go",
            package="example.com/m",
            version="latest",
            tags=(),
            pre_install=None,
            post_install=None,
            options={},
        )
        self.assertEqual(GoManager(FakeGo()).latest_version(tool), "1.10.0")


class BrewVersionTests(unittest.TestCase):
    """brew installed_version returns the highest installed keg, not the last one
    `brew list --versions` happens to print (brew does not sort that output)."""

    def test_installed_version_is_highest_keg_not_positional(self):
        from engine.domain import ResolvedTool
        from engine.managers.brew import BrewManager

        class FakeBrew(CommandRunner):
            def run(self, args, *, capture=True, read_only=False, env=None):
                if args[:3] == ["brew", "list", "--versions"]:
                    # highest keg listed first; positional [-1] would pick the older 1.9.3
                    return CommandResult(0, "libgit2 1.9.4 1.9.3\n", "")
                return CommandResult(0, "", "")

            def which(self, program):
                return "/opt/homebrew/bin/brew"

        tool = ResolvedTool(
            name="libgit2",
            manager="brew",
            package="libgit2",
            version="latest",
            tags=(),
            pre_install=None,
            post_install=None,
            options={},
        )
        self.assertEqual(BrewManager(FakeBrew()).installed_version(tool), "1.9.4")


class BrewfileManifestSyncTests(unittest.TestCase):
    """platform/mac/Brewfile and software.toml are two install paths for the same
    brew software (brew bundle vs the engine's brew adapter); guard against drift."""

    def test_brewfile_matches_macos_brew_tools_in_manifest(self):
        import re

        from engine.toml_io import TomlManifestStore

        root = Path(__file__).resolve().parent.parent
        manifest = TomlManifestStore(root / "software.toml").load()

        formulae: set[str] = set()
        casks: set[str] = set()
        for resolved in manifest.for_platform("macos"):
            if resolved.manager != "brew":
                continue
            (casks if resolved.options.get("cask") else formulae).add(resolved.package)

        text = (root / "platform" / "mac" / "Brewfile").read_text()
        self.assertEqual(formulae, set(re.findall(r'^brew "([^"]+)"', text, re.MULTILINE)))
        self.assertEqual(casks, set(re.findall(r'^cask "([^"]+)"', text, re.MULTILINE)))


class PinThrashTests(unittest.TestCase):
    """sync must not reinstall a tool whose pin the manager can never satisfy."""

    def _engine(self, manager):
        from engine.services import Engine

        path = Path(tempfile.mktemp(suffix=".toml"))
        # rg pinned to 14.0.0 via the manager named to match the stub.
        TomlManifestStore(path).save(
            Manifest(tools=(tool(manager=manager.name, version="14.0.0", platforms=("macos",)),))
        )
        return Engine(
            manifest_store=TomlManifestStore(path),
            lock_store=JsonLockStore(Path(tempfile.mktemp())),
            managers=_OneManager(manager),
            runner=FakeRunner(),
            console=_SilentConsole(),
            clock=_FixedClock(),
            platform="macos",
        )

    def test_unsatisfiable_pin_is_not_reinstalled(self):
        mgr = _StubManager(
            FakeRunner(), name="brewish", installs_exact_version=False, current="15.0.0"
        )
        outcome = self._engine(mgr).sync(assume_yes=True)
        self.assertTrue(outcome.ok)
        self.assertEqual(mgr.installs, [])  # no thrash

    def test_satisfiable_pin_drift_does_reinstall(self):
        mgr = _StubManager(
            FakeRunner(), name="cargoish", installs_exact_version=True, current="15.0.0"
        )
        self._engine(mgr).sync(assume_yes=True)
        self.assertEqual(mgr.installs, ["rg"])  # drift gets fixed


class PinCommandTests(unittest.TestCase):
    """`pin NAME VERSION` must enforce the new version, not re-pin the old one."""

    def _engine(self, manager, *, manifest_version):
        from engine.services import Engine

        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(
            Manifest(
                tools=(tool(manager=manager.name, version=manifest_version, platforms=("macos",)),)
            )
        )
        return Engine(
            manifest_store=TomlManifestStore(path),
            lock_store=JsonLockStore(Path(tempfile.mktemp())),
            managers=_OneManager(manager),
            runner=FakeRunner(),
            console=_SilentConsole(),
            clock=_FixedClock(),
            platform="macos",
        )

    def test_repin_hands_manager_the_new_version(self):
        # Re-pinning an already-pinned exact-version tool must resolve the updated
        # manifest entry, so cargo/pipx/go force-install the new pin — not the old.
        mgr = _StubManager(
            FakeRunner(), name="cargoish", installs_exact_version=True, current="1.0.0"
        )
        self._engine(mgr, manifest_version="1.0.0").pin("rg", "2.0.0")
        self.assertEqual(mgr.pinned_versions, ["2.0.0"])


class _HealthRunner(CommandRunner):
    """Runner that fails any bash command containing ``fail_marker`` (read-only probes)."""

    def __init__(self, fail_marker: str):
        self.fail_marker = fail_marker
        self.ran: list[str] = []

    def run(self, args, *, capture=True, read_only=False, env=None):
        cmd = args[2] if len(args) > 2 else ""
        self.ran.append(cmd)
        return CommandResult(1 if self.fail_marker in cmd else 0, "", "")

    def which(self, program):
        return "/usr/bin/" + program


class DoctorHealthCheckTests(unittest.TestCase):
    def test_doctor_runs_health_check_not_post_install(self):
        from engine.services import Engine

        path = Path(tempfile.mktemp(suffix=".toml"))
        TomlManifestStore(path).save(
            Manifest(
                tools=(
                    tool(
                        name="rg",
                        manager="brewish",
                        platforms=("macos",),
                        post_install="should-not-run",
                        health_check="HEALTHCMD",
                    ),
                )
            )
        )
        runner = _HealthRunner(fail_marker="HEALTHCMD")
        mgr = _StubManager(
            FakeRunner(), name="brewish", installs_exact_version=False, current="14.1.0"
        )
        report = json.loads(
            _capture_stdout(
                lambda: Engine(
                    manifest_store=TomlManifestStore(path),
                    lock_store=JsonLockStore(Path(tempfile.mktemp())),
                    managers=_OneManager(mgr),
                    runner=runner,
                    console=_SilentConsole(),
                    clock=_FixedClock(),
                    platform="macos",
                ).doctor(as_json=True)
            )
        )
        self.assertFalse(report["ok"])
        self.assertEqual(report["health_failures"][0]["check"], "HEALTHCMD")
        self.assertNotIn("should-not-run", runner.ran)  # post_install was not used


class CommandRegistryTests(unittest.TestCase):
    # A valid argv for each command (positionals filled in) — every registered
    # command must parse and resolve, so a missing wire fails loudly here.
    _ARGV = {
        "bootstrap": ["bootstrap"],
        "sync": ["sync"],
        "list": ["list"],
        "status": ["status"],
        "update": ["update"],
        "add": ["add", "x"],
        "remove": ["remove", "x"],
        "pin": ["pin", "x"],
        "unpin": ["unpin", "x"],
        "doctor": ["doctor"],
        "export": ["export"],
        "config": ["config", "list"],
        "why": ["why", "x"],
        "completion": ["completion", "bash"],
    }

    def test_every_command_parses_and_resolves(self):
        from engine.__main__ import build_parser
        from engine.commands import COMMANDS, COMMANDS_BY_NAME

        names = {c.name for c in COMMANDS}
        self.assertEqual(set(self._ARGV), names)  # argv table must cover the registry
        parser = build_parser()
        for name, argv in self._ARGV.items():
            parsed = parser.parse_args(argv)
            self.assertEqual(parsed.command, name)
            self.assertTrue(callable(COMMANDS_BY_NAME[name].run))


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


class ApplyEnvTests(unittest.TestCase):
    """The per-tool [env] overlay must set vars for the provisioning span and then
    fully restore os.environ — including when the body raises, since it wraps the
    manager install plus both hooks."""

    def test_sets_then_removes_a_new_variable(self):
        import os

        from engine.services import _apply_env

        key = "ZCONFIG_TEST_ENV_NEW"
        os.environ.pop(key, None)
        with _apply_env({key: "1"}):
            self.assertEqual(os.environ[key], "1")
        self.assertNotIn(key, os.environ)  # absent before -> removed after

    def test_restores_a_preexisting_variable(self):
        import os

        from engine.services import _apply_env

        key = "ZCONFIG_TEST_ENV_PRE"
        os.environ[key] = "original"
        try:
            with _apply_env({key: "override"}):
                self.assertEqual(os.environ[key], "override")
            self.assertEqual(os.environ[key], "original")  # restored, not removed
        finally:
            os.environ.pop(key, None)

    def test_restores_even_when_the_body_raises(self):
        import os

        from engine.services import _apply_env

        key = "ZCONFIG_TEST_ENV_RAISE"
        os.environ.pop(key, None)
        with self.assertRaises(RuntimeError), _apply_env({key: "1"}):
            raise RuntimeError("boom")
        self.assertNotIn(key, os.environ)  # cleaned up despite the exception

    def test_empty_env_is_a_noop(self):
        import os

        from engine.services import _apply_env

        before = dict(os.environ)
        with _apply_env({}):
            pass
        self.assertEqual(dict(os.environ), before)


if __name__ == "__main__":
    unittest.main()
