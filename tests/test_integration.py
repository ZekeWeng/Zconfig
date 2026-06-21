"""End-to-end tests through the CLI entry point.

Unlike test_engine.py (which unit-tests pieces with fakes), these drive the real
``main()`` — the composition root wiring the real SystemRunner, TOML/JSON stores,
and the script adapter — so the whole stack is exercised. They use the ``script``
manager with harmless touch/rm commands, so no real package manager is needed and
they run anywhere bash exists.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from engine.__main__ import main

_DEMO_MANIFEST = """\
[tools.demo]
manager = "script"
package = "demo"

[tools.demo.options]
check = "test -f {flag}"
install = "touch {flag}"
uninstall = "rm -f {flag}"
"""


class FullCycleIntegration(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.flag = self.dir / "flag"
        self.manifest = self.dir / "software.toml"
        self.lock = self.dir / "lock.json"
        self.log = self.dir / "log"
        self.manifest.write_text(_DEMO_MANIFEST.format(flag=self.flag))

    def _run(self, *args) -> int:
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            return main(
                [
                    "--manifest",
                    str(self.manifest),
                    "--lock",
                    str(self.lock),
                    "--log-file",
                    str(self.log),
                    *args,
                ]
            )

    def _locked(self) -> dict:
        return json.loads(self.lock.read_text())["tools"]

    def test_install_then_idempotent_then_orphan_remove(self):
        # install
        self.assertEqual(self._run("sync", "--yes"), 0)
        self.assertTrue(self.flag.exists())
        self.assertIn("demo", self._locked())

        # re-running converges with no change
        self.assertEqual(self._run("sync", "--yes"), 0)
        self.assertTrue(self.flag.exists())

        # drop from the manifest -> orphan deprovisioned on next sync
        self.manifest.write_text('[tools.other]\nmanager = "manual"\npackage = "other"\n')
        self.assertEqual(self._run("sync", "--yes"), 0)
        self.assertFalse(self.flag.exists())
        self.assertEqual(self._locked(), {})

    def test_add_with_health_check_writes_the_field(self):
        code = self._run(
            "add",
            "widget",
            "--manager",
            "manual",
            "--package",
            "widget",
            "--health-check",
            "widget --version",
            "--yes",
        )
        self.assertEqual(code, 0)
        self.assertIn('health_check = "widget --version"', self.manifest.read_text())

    def test_dry_run_changes_nothing(self):
        self.assertEqual(self._run("sync", "--dry-run", "--yes"), 0)
        self.assertFalse(self.flag.exists())  # install command never ran
        self.assertFalse(self.lock.exists())  # lock never written

    def test_status_json_reflects_installed_state(self):
        self._run("sync", "--yes")
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(io.StringIO()):
            code = main(
                [
                    "--manifest",
                    str(self.manifest),
                    "--lock",
                    str(self.lock),
                    "--log-file",
                    str(self.log),
                    "status",
                    "--json",
                ]
            )
        self.assertEqual(code, 0)
        rows = json.loads(sink.getvalue())
        demo = next(r for r in rows if r["name"] == "demo")
        self.assertEqual(demo["status"], "ok")


if __name__ == "__main__":
    unittest.main()
