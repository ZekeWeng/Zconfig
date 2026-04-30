# zconfig

Cross-platform dotfiles (macOS + Linux): Neovim, Zsh + Starship, Git, Tmux, plus a curated CLI toolset (fzf, ripgrep, fd, bat, eza, lazygit, gh) and language toolchains (Node, Python/uv, Go, Rust, Elixir).

## Install

```bash
git clone https://github.com/ZekeWeng/Zconfig.git ~/.zconfig
cd ~/.zconfig && make install
exec zsh
```

macOS prereqs: `xcode-select --install` and Homebrew. Run `make` (no args) for the menu.

| Target | What it does |
|---|---|
| `make install` | Full install — symlinks + per-tool downloads (brew bundle, apt repos, pinned binaries) |
| `make install-corp` | Configs + identity only. No downloads, no sudo, no GitHub clones. For corp-managed environments where IT installs tooling |
| `make update`  | Pull repo, brew upgrade, apt/dnf/pacman upgrade, refresh VSCode + Claude Code, sync nvim plugins |
| `make backup`  | Snapshot `~/` dotfiles to `~/.zconfig_backup` |
| `make check`   | `bash -n` every shell script |
| `make lint`    | shellcheck every shell script |

Configs are symlinked, so editing `~/.zconfig/...` applies live.

### Corp profile

`make install-corp` (or `ZCONFIG_PROFILE=corp make install`) runs only the steps that touch your `$HOME` directly: symlinks, SSH key/config, `~/.gitconfig.local` from `.env`. It skips every `run_installer`, `brew bundle`, `lazy.nvim` clone, and `pre-commit` install. Use it when corp IT manages package installation. Tools that aren't on PATH yet just no-op silently inside the configs (e.g., the `.zshrc` blocks for `starship`/`fzf`/`eza` are `command -v`-guarded).

One caveat: first `nvim` launch will still try to clone `lazy.nvim` from GitHub via `init.lua`'s self-bootstrap. If your network blocks `github.com`, vendor `lazy.nvim` into `~/.local/share/nvim/lazy/lazy.nvim` ahead of time.

## Troubleshoot

```bash
find ~ -type l ! -exec test -e {} \; -delete && make install   # broken symlinks
rm -rf ~/.local/share/nvim && nvim                             # reset nvim plugins
```

---

## Architecture

Hexagonal: dependencies point inward. `install.sh` is the composition root; everything else is a single-purpose module. Code that's coupled by functionality lives in the same folder — each tool ships its installer and config side-by-side under `tools/<category>/<tool>/`.

```
Makefile                  # user-facing menu — `make install/update/backup/check/lint`
  └── install.sh          # composition root
        ├── bootstrap/<step>.sh        # cross-cutting setup (clone, env, symlinks)
        ├── platform/<os>/install.sh   # platform adapter — brew bundle / run_installer ...
        │     └── tools/<category>/<tool>/install.sh   # one tool — install_<tool>()
        │           ├── config/        # the tool's config files (symlinked into $HOME)
        │           └── *.sh           # any tool-specific setup (e.g. neovim/lazy.sh)
        └── lib/<helper>.sh            # pure helpers, no I/O
```

**Rules.** `lib/` never sources installers. Installers never source each other. Cross-cutting bootstrap depends only on `lib/`.

### `tools/<category>/`

Tools are grouped by what they do for the user, not by tech stack.

| Category | Tools | What it covers |
|---|---|---|
| `shell/`    | `zsh`, `starship` | interactive shell + prompt view |
| `terminal/` | `tmux`, `ssh` | terminal sessions + remote connections |
| `editor/`   | `neovim`, `vscode` | text editing |
| `workflow/` | `git`, `precommit` | version control + commit hooks |
| `ai/`       | `claude-code`, `codex` | AI coding CLIs |
| `cli/`      | `eza`, `lazygit`, `gh`, `uv`, `tree-sitter` | general utilities |
| `fonts/`    | `nerd-fonts` | terminal fonts |
| `base/`     | `essentials` | distro base packages (Linux only) |

Each tool folder contains whatever it needs and nothing else: `install.sh` (if it installs a binary), `config/` (if it owns dotfiles), and any tool-specific helpers (`neovim/lazy.sh`, `git/render.sh`, `ssh/render.sh`).

`.claude/`, `.github/`, and `.pre-commit-config.yaml` stay at repo root because their respective tools require it there.

### Layers

| Layer | Files | Function naming |
|---|---|---|
| Composition root | `install.sh` | — |
| Cross-cutting bootstrap | `bootstrap/*.sh` | verbs (`link_configs`, `ensure_env_file`) |
| Platform adapters | `platform/{mac,linux}/install.sh` | — |
| Tool installers | `tools/<category>/<name>/install.sh` | `install_<name>()` (hyphens → underscores) |
| Tool-specific setup | `tools/<category>/<name>/*.sh` | verbs (`bootstrap_ssh`, `write_gitconfig_local`, `install_lazy_nvim`) |
| Pure helpers | `lib/{common,verify,pkg,arch,bootstrap,env}.sh` | — |

### `lib/`

| File | Exports |
|---|---|
| `bootstrap.sh` | sources every other lib, idempotent |
| `common.sh` | `log_info` / `log_ok` / `log_err`, `load_installer`, `run_installer` |
| `env.sh` | `load_env` — safe key=value parser, sourced by `install.sh` and `.zshenv` |
| `verify.sh` | `verify_sha256`, `verify_and_download`, `verify_and_run` |
| `pkg.sh` | `$PKG_MANAGER`, `pkg_install`, `pkg_update_lists`, `pkg_has` |
| `arch.sh` | `$OS_KIND`, `$ARCH`, `$ARCH_ALT` |

### `bootstrap/`

| File | Function |
|---|---|
| `env.sh` | `ensure_env_file` — seed `.env` from `.env.example` on first install |
| `symlinks.sh` | `link_configs` — single source-of-truth symlink table |

Tool-specific setup that used to live here moved next to its tool: `lazy_nvim` → `tools/editor/neovim/lazy.sh`, `ssh` render → `tools/terminal/ssh/render.sh`, `git` render → `tools/workflow/git/render.sh`, `precommit` → `tools/workflow/precommit/install.sh`.

### Installer strategies

| Tool | Strategy |
|---|---|
| `base/essentials` | distro packages (Linux); reconciles `fdfind`→`fd`, `batcat`→`bat` |
| `editor/neovim` | pinned AppImage + per-arch SHA256 |
| `cli/eza`, `cli/lazygit`, `cli/gh` | signed apt repo where possible, distro pkg otherwise |
| `editor/vscode` | macOS direct download w/ SHA256; Linux MS apt repo. Auto-update disabled at install — bundle stays at the version `make install` last fetched |
| `shell/starship`, `cli/uv` | distro pkg first, hash-verified upstream installer fallback |
| `fonts/nerd-fonts` | pinned release zips + SHA256 per font |
| `ai/claude-code` | hash-verified `claude.ai/install.sh` |
| `ai/codex` | pinned native binary (Linux); brew cask (macOS) |

### Conventions

- Idempotent: every installer guards on `command -v <tool>`; bootstrap steps are safe to re-run. Version-floor checks (e.g. `neovim`) live in installers only when a wrong version actively breaks something downstream — otherwise rely on `update.sh` to refresh.
- Re-source guards (`[[ -n "${_ZCONFIG_*_LOADED:-}" ]] && return 0`) live on files sourced from `install.sh` or `lib/bootstrap.sh`. Files dispatched once via `run_installer` don't need them.
- Pinned: every download has `<TOOL>_VERSION` + `<TOOL>_*_SHA256`. Bump = edit one file.
- Errors: orchestrators run `set -euo pipefail`. Recoverable failures must be in `if`/`||`.
- Logging: use `log_*` from `lib/common.sh`. Never raw `echo -e` with color codes.
- `load_installer <name>` resolves by globbing `tools/*/<name>/install.sh` — the platform script doesn't need to know the category.

### Adding things

- **New symlink:** add an entry to the `ZCONFIG_SYMLINKS` array in `bootstrap/symlinks.sh` (used by both `link_configs` and `scripts/backup.sh`).
- **New tool:** drop `tools/<category>/<name>/install.sh` defining `install_<name>()`; add `run_installer <name>` to the platform script. If it owns a config, put it in `tools/<category>/<name>/config/` and add a symlink.
- **New cross-cutting bootstrap step:** drop `bootstrap/<step>.sh` defining one function; source it and call it from `install.sh`.
- **New platform:** mirror `platform/linux/install.sh`, add a case to `install.sh`.

### Bumping pinned versions

Each installer has the bump command at the top, e.g.:

```bash
# curl -fsSL https://claude.ai/install.sh | shasum -a 256
```

Fetch artifact → recompute SHA → paste into the installer → commit. CI re-runs shellcheck + gitleaks.

### Test one installer in isolation

```bash
bash -c 'source ~/.zconfig/lib/bootstrap.sh && run_installer claude-code'
```

---

MIT.
