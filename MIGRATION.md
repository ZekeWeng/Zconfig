# Migration — adding the `zconfig` declarative engine

This change **adds** a declarative software-management engine on top of the
existing dotfiles installer. It is intentionally additive and coexisting:
nothing that already worked was moved, renamed, or deleted.

## Nothing was restructured

The following kept their exact location and behavior:

- `install.sh`, `bootstrap.sh`, `Makefile` (only new targets appended)
- `platform/{mac,linux}/install.sh`, both `Brewfile`s
- `tools/<category>/<tool>/` — every per-tool installer and config
- `lib/`, `bootstrap/`, `scripts/`

If you do nothing differently, `make install` / `make update` behave exactly as
before.

## What was added

| Path | Purpose |
|------|---------|
| `software.toml` | The declarative manifest — single source of truth for every managed tool |
| `bin/zconfig` | Zero-dependency bash entrypoint; finds Python 3.11+ and runs the engine |
| `engine/` | The engine (pure-stdlib Python, hexagonal): `domain` core, `ports`, `managers/` adapters, `services`, `commands` CLI table, `__main__` composition root |
| `zconfig.lock` | Per-machine record of what `zconfig` installed (gitignored) |
| `.zconfig.log` | Per-machine run log (gitignored) |
| `MIGRATION.md` | This file |

`Makefile` gained `status`, `sync`, and `doctor` targets. `.gitignore` gained
`zconfig.lock` and `.zconfig.log`.

## How the new and old layers relate

The manifest is the new cross-manager source of truth, but it **delegates**
rather than reimplements:

- **macOS / brew** — the `brew` adapter shells out to `brew`. The `Brewfile`
  remains the reference for what brew installs; the manifest mirrors it so the
  same tools gain drift detection, pinning, lockfile tracking, and update
  prompts. (The brew adapter and the Brewfile are not auto-synced — if you add a
  formula to one, add it to the other, or run `zconfig export` to snapshot.)
- **Linux bespoke installs** — tools with a pinned `tools/<...>/install.sh`
  (neovim, eza, lazygit, gh, starship, uv, tree-sitter, nerd-fonts,
  claude-code, codex) are declared with `manager = "script"` and an `install`
  that delegates: `source "$ZCONFIG_DIR/lib/bootstrap.sh" && run_installer <name>`.
  The manifest decides *whether* a tool should be present; the existing
  installer decides *how* it is installed (with its SHA-pinned download).

## Adopting it

1. `./bin/zconfig status` — read-only; shows how your machine compares to
   `software.toml`. Safe to run anytime.
2. `./bin/zconfig sync --dry-run` — preview what a converge would do.
3. `./bin/zconfig sync` — install missing tools and record them in the lock.
   Existing hand-installed tools are left alone (they are not in the lock).

There is no data migration and no irreversible step. Deleting `software.toml`,
`zconfig.lock`, and `engine/` returns the repo to its prior dotfiles-only state.
