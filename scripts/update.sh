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

RECAP_ITEMS=()

recap_add() {
    RECAP_ITEMS+=("$1")
}

first_line() {
    "$@" 2> /dev/null | sed -n '1p' || true
}

version_or_missing() {
    local label="$1"
    local cmd="$2"
    shift 2

    if command -v "$cmd" &> /dev/null; then
        local version
        version="$(first_line "$cmd" "$@")"
        printf '  %-13s %s\n' "$label:" "${version:-installed (version unavailable)}"
    else
        printf '  %-13s %s\n' "$label:" "not installed"
    fi
}

log_ok "Updating system and dotfiles..."

# ── Dotfiles repo ────────────────────────────────────────
if [[ -d "$ZCONFIG_DIR/.git" ]]; then
    if ! git -C "$ZCONFIG_DIR" rev-parse HEAD &> /dev/null; then
        log_info "Skipping dotfiles pull (no commits yet)"
        recap_add "Dotfiles: skipped (no commits yet)"
    elif [[ -n "$(git -C "$ZCONFIG_DIR" status --porcelain)" ]]; then
        log_info "Skipping dotfiles pull (uncommitted changes)"
        recap_add "Dotfiles: skipped (uncommitted changes)"
    else
        log_info "Pulling dotfiles..."
        branch="$(git -C "$ZCONFIG_DIR" rev-parse --abbrev-ref HEAD)"
        if [[ "$branch" == "HEAD" ]]; then
            log_err "  detached HEAD; skipping pull"
            recap_add "Dotfiles: skipped (detached HEAD)"
        elif git -C "$ZCONFIG_DIR" pull origin "$branch"; then
            log_ok "  dotfiles up to date (branch: $branch)"
            recap_add "Dotfiles: pulled branch $branch"
        else
            log_err "  pull failed; continuing with rest of update"
            recap_add "Dotfiles: pull failed"
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
        recap_add "Homebrew: updated packages, casks, and cleanup"
    else
        recap_add "Homebrew: skipped (brew not installed)"
    fi

    # VSCode is direct-download (not in Brewfile). Auto-update is locked
    # to 'manual' at install, so we refresh it here on demand.
    if [[ -d "/Applications/Visual Studio Code.app" ]]; then
        log_info "Updating VSCode (direct download)..."
        rm -rf "/Applications/Visual Studio Code.app"
        command -v brew &> /dev/null && rm -f "$(brew --prefix)/bin/code"
        run_installer vscode
        recap_add "VSCode: refreshed direct-download app"
    else
        recap_add "VSCode: skipped (app not found)"
    fi
fi

# ── Linux: distro packages ───────────────────────────────
if [[ "$(uname)" == "Linux" ]]; then
    case "${PKG_MANAGER:-}" in
        apt)    log_info "Upgrading apt packages..."; sudo apt-get update && sudo apt-get upgrade -y; recap_add "System packages: upgraded with apt" ;;
        dnf)    log_info "Upgrading dnf packages...";  sudo dnf upgrade -y; recap_add "System packages: upgraded with dnf" ;;
        pacman) log_info "Upgrading pacman packages..."; sudo pacman -Syu --noconfirm; recap_add "System packages: upgraded with pacman" ;;
        *)      log_info "  no recognized package manager; skipping system upgrade"; recap_add "System packages: skipped (no recognized package manager)" ;;
    esac
fi

# ── Claude Code (upstream installer always fetches latest) ─
if command -v claude &> /dev/null; then
    log_info "Updating Claude Code..."
    rm -f "$(command -v claude)"
    run_installer claude-code
    recap_add "Claude Code: refreshed from upstream installer"
else
    recap_add "Claude Code: skipped (claude not installed)"
fi

# ── Neovim plugins ───────────────────────────────────────
if command -v nvim &> /dev/null; then
    log_info "Syncing Neovim plugins..."
    nvim --headless "+Lazy! sync" +qa
    log_ok "  plugins synced"
    recap_add "Neovim plugins: synced with Lazy"
else
    recap_add "Neovim plugins: skipped (nvim not installed)"
fi

# ── Language toolchains ──────────────────────────────────
if command -v rustup &> /dev/null; then
    log_info "Updating Rust..."
    rustup update
    recap_add "Rust: updated rustup toolchains"
else
    recap_add "Rust: skipped (rustup not installed)"
fi

if command -v npm &> /dev/null; then
    log_info "Updating npm globals..."
    npm update -g
    recap_add "npm globals: updated"
else
    recap_add "npm globals: skipped (npm not installed)"
fi

# ── Summary ──────────────────────────────────────────────
log_ok "Update complete."
log_ok "Update recap"

printf '\n%bActions%b\n' "$_ZCONFIG_YELLOW" "$_ZCONFIG_NC"
for item in "${RECAP_ITEMS[@]}"; do
    printf '  - %s\n' "$item"
done

printf '\n%bSystem%b\n' "$_ZCONFIG_YELLOW" "$_ZCONFIG_NC"
printf '  %-13s %s\n' "OS:" "$(uname -srm)"
command -v sw_vers &> /dev/null && printf '  %-13s %s\n' "macOS:" "$(sw_vers -productVersion)"
[[ -n "${PKG_MANAGER:-}" ]] && printf '  %-13s %s\n' "Pkg manager:" "$PKG_MANAGER"

if [[ -d "$ZCONFIG_DIR/.git" ]] && git -C "$ZCONFIG_DIR" rev-parse HEAD &> /dev/null; then
    branch="$(git -C "$ZCONFIG_DIR" rev-parse --abbrev-ref HEAD)"
    commit="$(git -C "$ZCONFIG_DIR" rev-parse --short HEAD)"
    printf '  %-13s %s @ %s\n' "Zconfig:" "$branch" "$commit"
fi

printf '\n%bAI tools%b\n' "$_ZCONFIG_YELLOW" "$_ZCONFIG_NC"
version_or_missing "Claude Code" claude --version
version_or_missing "Codex" codex --version

printf '\n%bEditors and CLIs%b\n' "$_ZCONFIG_YELLOW" "$_ZCONFIG_NC"
version_or_missing "Homebrew" brew --version
version_or_missing "VSCode" code --version
version_or_missing "Neovim" nvim --version
version_or_missing "Git" git --version
version_or_missing "Node" node --version
version_or_missing "npm" npm --version
version_or_missing "Python" python3 --version
version_or_missing "Rust" rustc --version
