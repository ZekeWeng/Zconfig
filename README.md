# Zconfig

Cross-platform dotfiles for macOS and Linux. One command bootstraps a complete dev environment — editor, shell, languages, AI tooling — on a fresh machine.

## Features

- **Editor** — Neovim (lazy.nvim, LSP, treesitter) and VSCode, both pinned
- **Shell** — Zsh + Starship prompt, with fzf, ripgrep, fd, bat, eza, htop
- **Terminal** — tmux session config and SSH client setup
- **Version control** — Git, lazygit, gh, pre-commit hooks
- **AI tooling** — Claude Code and Codex CLIs
- **Languages** — Node, Python (uv), Go, Rust, Elixir
- **Cross-platform** — One install path across macOS (Homebrew) and Linux (apt/dnf/pacman)
- **Reproducible** — every download pinned with SHA256, every step idempotent
- **Corp-friendly** — `install-corp` profile for managed machines: configs + identity, no downloads, no sudo

## Quick start

```bash
git clone https://github.com/ZekeWeng/Zconfig.git ~/.zconfig
cd ~/.zconfig && make install
exec zsh
```

macOS prereqs: `xcode-select --install` and Homebrew. Run `make` (no args) for the menu.

| Target | What it does |
|---|---|
| `make install` | Symlinks + per-tool installs (brew bundle, apt repos, pinned binaries) |
| `make install-corp` | Configs + identity only — no downloads, no sudo. For corp-managed machines |
| `make update` | Pull repo, upgrade packages, refresh nvim plugins / VSCode / Claude Code |
| `make backup` | Snapshot `~/` dotfiles to `~/.zconfig_backup` |

Develop with `make check` (syntax) and `make lint` (shellcheck).

## Customize

- **Identity** — first install seeds `.env` from `.env.example`. Set your name and email there; they render into `~/.gitconfig.local` and SSH config.
- **Live edits** — configs are symlinked, so editing `~/.zconfig/...` applies on the next shell.
- **Corp environments** — `make install-corp` skips every download, package install, and GitHub clone. Configs that reference missing tools are `command -v`-guarded and no-op silently. Caveat: first `nvim` launch still tries to clone `lazy.nvim` from GitHub — vendor it into `~/.local/share/nvim/lazy/lazy.nvim` ahead of time if you're firewalled.

---

## Architecture

Hexagonal: dependencies point inward. `install.sh` is the composition root; everything else is single-purpose. Each tool ships its installer and config side-by-side under `tools/<category>/<tool>/`.

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
