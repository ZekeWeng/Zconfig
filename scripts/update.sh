#!/bin/bash
# Pulls the dotfiles repo, then refreshes everything that has a maintained
# update path: brew, apt/dnf/pacman, direct-download apps (VSCode, Claude
# Code), nvim plugins, rust, npm. Each block guards on tool presence so the
# script runs cleanly on a partial install.
#
# Pinned binaries (codex, lazygit, neovim AppImage, nerd-fonts) only move
# when you bump their SHA in the repo — `make update` won't touch them.

set -euo pipefail
IFS=$'\n\t'

ZCONFIG_DIR="${ZCONFIG_DIR:-$HOME/.zconfig}"
source "$ZCONFIG_DIR/lib/bootstrap.sh"

log_ok "Updating system and dotfiles..."

# ── Dotfiles repo ────────────────────────────────────────
if [[ -d "$ZCONFIG_DIR/.git" ]]; then
    if ! git -C "$ZCONFIG_DIR" rev-parse HEAD &> /dev/null; then
        log_info "Skipping dotfiles pull (no commits yet)"
    elif [[ -n "$(git -C "$ZCONFIG_DIR" status --porcelain)" ]]; then
        log_info "Skipping dotfiles pull (uncommitted changes)"
    else
        log_info "Pulling dotfiles..."
        branch="$(git -C "$ZCONFIG_DIR" rev-parse --abbrev-ref HEAD)"
        if [[ "$branch" == "HEAD" ]]; then
            log_err "  detached HEAD; skipping pull"
        elif git -C "$ZCONFIG_DIR" pull origin "$branch"; then
            log_ok "  dotfiles up to date (branch: $branch)"
        else
            log_err "  pull failed; continuing with rest of update"
        fi
    fi
fi

# ── macOS: brew + direct-download apps ───────────────────
if [[ "$(uname)" == "Darwin" ]]; then
    if command -v brew &> /dev/null; then
        log_info "Updating Homebrew..."
        brew update && brew upgrade && brew cleanup --prune=all
        [[ -f "$ZCONFIG_DIR/platform/mac/Brewfile" ]] && brew bundle --file="$ZCONFIG_DIR/platform/mac/Brewfile"
        log_ok "  Homebrew up to date"
    fi

    # VSCode is direct-download (not in Brewfile). Auto-update is locked
    # to 'manual' at install, so we refresh it here on demand.
    if [[ -d "/Applications/Visual Studio Code.app" ]]; then
        log_info "Updating VSCode (direct download)..."
        rm -rf "/Applications/Visual Studio Code.app"
        rm -f "$(brew --prefix)/bin/code"
        run_installer vscode
    fi
fi

# ── Linux: distro packages ───────────────────────────────
if [[ "$(uname)" == "Linux" ]]; then
    case "${PKG_MANAGER:-}" in
        apt)    log_info "Upgrading apt packages..."; sudo apt-get update && sudo apt-get upgrade -y ;;
        dnf)    log_info "Upgrading dnf packages...";  sudo dnf upgrade -y ;;
        pacman) log_info "Upgrading pacman packages..."; sudo pacman -Syu --noconfirm ;;
        *)      log_info "  no recognized package manager; skipping system upgrade" ;;
    esac
fi

# ── Claude Code (upstream installer always fetches latest) ─
if command -v claude &> /dev/null; then
    log_info "Updating Claude Code..."
    rm -f "$(command -v claude)"
    run_installer claude-code
fi

# ── Neovim plugins ───────────────────────────────────────
if command -v nvim &> /dev/null; then
    log_info "Syncing Neovim plugins..."
    nvim --headless "+Lazy! sync" +qa
    log_ok "  plugins synced"
fi

# ── Language toolchains ──────────────────────────────────
command -v rustup &> /dev/null && { log_info "Updating Rust...";   rustup update; }
command -v npm    &> /dev/null && { log_info "Updating npm globals..."; npm update -g; }

# ── Summary ──────────────────────────────────────────────
log_ok "Update complete."
command -v sw_vers &> /dev/null && log_info "macOS:    $(sw_vers -productVersion)"
command -v brew    &> /dev/null && log_info "Homebrew: $(brew --version | head -1)"
command -v code    &> /dev/null && log_info "VSCode:   $(code --version | head -1)"
command -v claude  &> /dev/null && log_info "Claude:   $(claude --version 2>/dev/null | head -1)"
command -v nvim    &> /dev/null && log_info "Neovim:   $(nvim --version | head -1)"
command -v git     &> /dev/null && log_info "Git:      $(git --version)"
command -v node    &> /dev/null && log_info "Node:     $(node --version)"
command -v python3 &> /dev/null && log_info "Python:   $(python3 --version)"
