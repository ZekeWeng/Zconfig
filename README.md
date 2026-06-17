# Zconfig

Cross-platform dotfiles for macOS and Linux. One command bootstraps a complete dev environment — editor, shell, languages, AI tooling — on a fresh machine.

## Features

- **Editor** — Neovim (lazy.nvim, LSP, treesitter) and VSCode, both pinned
- **Shell** — Zsh + Starship prompt, with fzf, ripgrep, fd, eza
- **Terminal** — tmux session config and SSH client setup
- **Version control** — Git, lazygit, gh, pre-commit hooks
- **AI tooling** — Claude Code and Codex CLIs
- **Languages** — Node, Python (uv), Go, Rust, Elixir
- **Cross-platform** — One install path across macOS (Homebrew) and Linux (apt/dnf/pacman)
- **Reproducible** — every download pinned with SHA256, every step idempotent
- **Corp-friendly** — `install-corp` profile: terminal styling (zsh + starship + tmux) plus a lean brew bundle (essentials + fonts). No languages, no DB/infra, no AI casks, no SSH/git identity.

## Quick start

One command on a fresh machine — clones to `~/.zconfig`, installs Homebrew if missing (macOS), prompts for your git identity, and runs the full install:

```bash
curl -fsSL https://raw.githubusercontent.com/ZekeWeng/Zconfig/main/bootstrap.sh | bash
```

Corp profile: `ZCONFIG_PROFILE=corp curl -fsSL ... | bash`. Or clone manually:

```bash
git clone https://github.com/ZekeWeng/Zconfig.git ~/.zconfig
cd ~/.zconfig && make install
exec zsh
```

macOS prereq: `xcode-select --install` (git). Run `make` (no args) for the menu.

| Target | What it does |
|---|---|
| `make install` | Symlinks + per-tool installs (brew bundle, apt repos, pinned binaries) |
| `make install-corp` | Terminal styling (zsh + starship + tmux) + lean brew bundle on macOS (essentials + fonts). No languages/DB/AI/identity |
| `make update` | Pull repo, upgrade packages, refresh nvim plugins / VSCode / Claude Code |
| `make backup` | Snapshot `~/` dotfiles to `~/.zconfig_backup` |
| `make status` | Show software drift vs `software.toml` (the `zconfig` engine) |
| `make sync` | Converge installed software to `software.toml` |
| `make doctor` | Check the `zconfig` environment health |

Develop with `make check` (syntax) and `make lint` (shellcheck).

## Customize

- **Identity** — first install prompts for your git name/email (skippable) and stores them in `.env` (gitignored); they render into `~/.gitconfig.local` and SSH config. Edit `.env` and re-run anytime.
- **Machine-local overrides** — `~/.zshrc.local`, `~/.gitconfig.local`, and `~/.ssh/config.local` are sourced/included but never committed. Extra brew packages go in `platform/mac/Brewfile.local` (gitignored).
- **Live edits** — configs are symlinked, so editing `~/.zconfig/...` applies on the next shell.
- **Existing dotfiles** — anything the installer would replace is moved aside to `<file>.bak.<timestamp>`, never overwritten.
- **Corp environments** — `make install-corp` links 4 dotfiles (`.zshrc`, `.zshenv`, `.tmux.conf`, `starship.toml`) and, on macOS with Homebrew available, runs `brew bundle --file=platform/mac/Brewfile.corp` (essentials + fonts only). No languages, no DB/infra, no AI casks, no VSCode/Claude Code direct downloads, no SSH key, no `~/.gitconfig`, no nvim config, no pre-commit. On Linux, corp does symlinks only.

---

## Declarative software management (`zconfig`)

Alongside the dotfiles installer, `zconfig` is a declarative engine that treats a single manifest — `software.toml` — as the source of truth for **every** tool on the machine, across package managers. It installs what's missing, flags what's outdated, removes what you've deleted from the manifest, and pins versions — idempotently, on macOS / Linux / WSL.

Run it via `./bin/zconfig <command>` (or the `make status`/`sync`/`doctor` shortcuts). It needs only Python 3.11+ (for stdlib `tomllib`) — no pip packages.

```
zconfig status     # show drift: missing / outdated / pinned / orphaned
zconfig sync       # install missing, fix pins, deprovision orphans (respects pins)
zconfig update     # interactively update outdated tools: [u]pdate [s]kip [p]in [a]ll
zconfig bootstrap  # fresh machine: ensure prerequisites, then sync
zconfig add NAME --manager brew --package NAME --add-tags core
zconfig remove NAME            # uninstall + strip from the manifest
zconfig pin NAME [VERSION]     # lock a version (default: the installed one)
zconfig unpin NAME             # track latest again
zconfig doctor                 # verify managers, health checks, orphans
zconfig export [--write]       # snapshot installed software into manifest form
```

Global flags: `--dry-run` (show actions, change nothing), `--yes` (assume yes), `--tags core,dev` (operate on a subset), `--manifest` / `--lock` / `--log-file` (override paths), `--version`. Every run appends to `$ZCONFIG_DIR/.zconfig.log`.

### Configuring defaults

Bake persistent defaults into an optional `[settings]` table so you don't repeat flags. Anything here is overridable per-run by a flag or environment variable.

```toml
[settings]
default_tags     = ["core"]   # commands act on this subset when no --tags is passed
default_platform = "linux"    # plan/converge as if on another OS
```

Resolution precedence is **flag / env var → `[settings]` → built-in default**:

| Knob | Env var | `[settings]` key | Flag |
|------|---------|------------------|------|
| Target platform | `ZCONFIG_PLATFORM` | `default_platform` | — |
| Tag subset | — | `default_tags` | `--tags` |
| Repo location | `ZCONFIG_DIR` | — | — |
| Manifest / lock / log paths | — | — | `--manifest` / `--lock` / `--log-file` |

`default_platform` (or `ZCONFIG_PLATFORM=linux`) lets a Mac preview exactly what a Linux converge would do — including the per-OS `overrides` — without leaving the laptop.

### The manifest

Each tool is one `[tools.<name>]` block. `manager` selects the backend; `version` is `latest` or an exact pin; `platforms` scopes it; `tags` group it for subset installs; `pre_install`/`post_install` are optional hooks (`post_install` doubles as a health check). Per-platform differences go in an `overrides` sub-table.

```toml
[tools.ripgrep]
manager   = "brew"
package   = "ripgrep"
version   = "latest"            # or pin: "14.1.0"
platforms = ["macos", "linux"]
tags      = ["core", "cli"]
post_install = "rg --version"

[tools.ripgrep.overrides.linux]  # apt calls it the same here, but this is where a
manager = "apt"                  # different package name / manager per-OS would go
package = "ripgrep"
```

**Add a tool:** `zconfig add NAME --manager <m> --package <p>` (interactive without flags), or hand-edit the file. **Remove:** `zconfig remove NAME` uninstalls and deletes the block — or just delete the block and run `zconfig sync`, which deprovisions it as an orphan. **Pin:** `zconfig pin NAME 14.1.0`; **unpin:** `zconfig unpin NAME`.

> `zconfig add/pin/remove` regenerate `software.toml` and do not preserve hand-written section comments below the file header (a deliberate tradeoff of the stdlib-only TOML writer).

### Safety model

A lockfile (`zconfig.lock`, gitignored) records what `zconfig` installed. Orphan removal **only** ever touches tools in that lock — software you installed by hand is never a removal candidate. Every destructive action prompts for confirmation (skip with `--yes`) and honors `--dry-run`. Pinned tools are never auto-updated.

**Trust model — a manifest is executable.** `script`/`manual` tools and `pre_install`/`post_install` hooks run their shell strings via `bash -c`, exactly like a `Makefile` or `Brewfile` does. Treat `software.toml` as code: only run `zconfig sync` against a manifest you trust, and review these fields before adopting someone else's. The engine itself never builds shell strings from external data — package names discovered by `zconfig export` land only in `name`/`package` fields, never in a command — and all package-manager calls pass argument lists (no shell interpolation), so the only execution surface is the shell strings you write yourself.

### Per-tool environment

Any tool can declare an `[env]` table that is exported only for its own install/update/hooks and restored afterward — handy for build flags or registries:

```toml
[tools.some-crate]
manager = "cargo"
package = "some-crate"

[tools.some-crate.env]
CARGO_NET_GIT_FETCH_WITH_CLI = "true"
RUSTFLAGS = "-C target-cpu=native"
```

### Relationship to the dotfiles installer

The two coexist. `install.sh` / the Brewfile remain the reference for *how* brew installs and how dotfiles are symlinked; the `zconfig` brew adapter **delegates** to `brew`, and Linux tools with a bespoke pinned installer delegate to it via the `script` manager (`run_installer <name>`). The manifest adds the cross-manager, lockfile, drift, and update-prompt layer on top — it does not replace the pinned installers. See `MIGRATION.md`.

### Writing a new adapter

Drop one file in `engine/managers/` that subclasses `PackageManager` and decorates itself with `@register`; it is auto-discovered with no edits to the core. Implement `is_available`, `is_installed`, `installed_version`, `latest_version`, `install`, `update`, `uninstall`, `pin` (see `engine/managers/cargo.py` for a compact example).

```python
from ..ports import CommandResult, PackageManager
from . import register

@register
class MyManager(PackageManager):
    name = "mymgr"
    def is_available(self): return self.runner.which("mymgr") is not None
    # ... implement the rest, using self.runner.run([...], read_only=True) for probes
```

---

## Architecture

Hexagonal: dependencies point inward. `install.sh` is the composition root for the dotfiles installer; `engine/__main__.py` is the composition root for the `zconfig` engine. Each tool ships its installer and config side-by-side under `tools/<category>/<tool>/`.

The `zconfig` engine follows the same rule: `engine/domain.py` is the pure core (no I/O), `engine/ports.py` the interfaces, `engine/managers/` + the `shell`/`console`/`toml_io`/`lockfile`/`platform` adapters the outside edge, `engine/services.py` the application layer, and `engine/__main__.py` the only place concretes are wired.

```
Makefile                  # user-facing menu
  └── install.sh          # composition root
        ├── bootstrap/<step>.sh        # cross-cutting setup (env, symlinks)
        ├── platform/<os>/install.sh   # platform adapter (brew / apt / dnf)
        │     └── tools/<category>/<tool>/install.sh
        │           ├── config/        # dotfiles (symlinked into $HOME)
        │           └── *.sh           # tool-specific setup
        └── lib/<helper>.sh            # pure helpers, no I/O
```

Tools are grouped by what they do for the user, not by tech stack:

| Category | Tools |
|---|---|
| `shell/`    | `zsh`, `starship` |
| `terminal/` | `tmux`, `ssh` |
| `editor/`   | `neovim`, `vscode` |
| `workflow/` | `git`, `precommit` |
| `ai/`       | `claude-code`, `codex` |
| `cli/`      | `eza`, `lazygit`, `gh`, `uv`, `tree-sitter` |
| `fonts/`    | `nerd-fonts` |
| `base/`     | `essentials` (Linux distro packages) |
