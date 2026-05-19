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

```bash
git clone https://github.com/ZekeWeng/Zconfig.git ~/.zconfig
cd ~/.zconfig && make install
exec zsh
```

macOS prereqs: `xcode-select --install` and Homebrew. Run `make` (no args) for the menu.

| Target | What it does |
|---|---|
| `make install` | Symlinks + per-tool installs (brew bundle, apt repos, pinned binaries) |
| `make install-corp` | Terminal styling (zsh + starship + tmux) + lean brew bundle on macOS (essentials + fonts). No languages/DB/AI/identity |
| `make update` | Pull repo, upgrade packages, refresh nvim plugins / VSCode / Claude Code |
| `make backup` | Snapshot `~/` dotfiles to `~/.zconfig_backup` |

Develop with `make check` (syntax) and `make lint` (shellcheck).

## Customize

- **Identity** — first install seeds `.env` from `.env.example`. Set your name and email there; they render into `~/.gitconfig.local` and SSH config.
- **Live edits** — configs are symlinked, so editing `~/.zconfig/...` applies on the next shell.
- **Corp environments** — `make install-corp` links 4 dotfiles (`.zshrc`, `.zshenv`, `.tmux.conf`, `starship.toml`) and, on macOS with Homebrew available, runs `brew bundle --file=platform/mac/Brewfile.corp` (essentials + fonts only). No languages, no DB/infra, no AI casks, no VSCode/Claude Code direct downloads, no SSH key, no `~/.gitconfig`, no nvim config, no pre-commit. On Linux, corp does symlinks only.

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
