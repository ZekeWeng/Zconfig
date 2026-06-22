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

# Run one maintenance step in a subshell that keeps `set -e` on (so a multi-
# command step still stops at its first failed command) without that failure
# aborting the whole update. The exit code lands in STEP_RC for the caller.
STEP_RC=0
try_step() {
    set +e
    ( set -e; "$@" )
    STEP_RC=$?
    set -e
}

_update_homebrew() {
    brew update
    brew upgrade
    brew cleanup --prune=all
    [[ -f "$ZCONFIG_DIR/platform/mac/Brewfile" ]] && brew bundle --file="$ZCONFIG_DIR/platform/mac/Brewfile"
    [[ -f "$ZCONFIG_DIR/platform/mac/Brewfile.local" ]] && brew bundle --file="$ZCONFIG_DIR/platform/mac/Brewfile.local"
    return 0
}

_update_vscode() {
    rm -rf "/Applications/Visual Studio Code.app"
    command -v brew &> /dev/null && rm -f "$(brew --prefix)/bin/code"
    run_installer vscode
}

_update_claude() {
    rm -f "$(command -v claude)"
    run_installer claude-code
}

_update_system_packages() {
    case "${PKG_MANAGER:-}" in
        apt)    sudo apt-get update && sudo apt-get upgrade -y ;;
        dnf)    sudo dnf upgrade -y ;;
        pacman) sudo pacman -Syu --noconfirm ;;
        *)      return 0 ;;
    esac
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
        try_step _update_homebrew
        if (( STEP_RC == 0 )); then
            log_ok "  Homebrew up to date"
            recap_add "Homebrew: updated packages, casks, and cleanup"
        else
            log_err "  Homebrew update failed; continuing"
            recap_add "Homebrew: update FAILED"
        fi
    else
        recap_add "Homebrew: skipped (brew not installed)"
    fi

    # VSCode is direct-download (not in Brewfile). Auto-update is locked
    # to 'manual' at install, so we refresh it here on demand.
    if [[ -d "/Applications/Visual Studio Code.app" ]]; then
        log_info "Updating VSCode (direct download)..."
        try_step _update_vscode
        if (( STEP_RC == 0 )); then
            recap_add "VSCode: refreshed direct-download app"
        else
            log_err "  VSCode update failed; continuing"
            recap_add "VSCode: update FAILED"
        fi
    else
        recap_add "VSCode: skipped (app not found)"
    fi
fi

# ── Linux: distro packages ───────────────────────────────
if [[ "$(uname)" == "Linux" ]]; then
    if [[ -z "${PKG_MANAGER:-}" ]]; then
        log_info "  no recognized package manager; skipping system upgrade"
        recap_add "System packages: skipped (no recognized package manager)"
    else
        log_info "Upgrading system packages ($PKG_MANAGER)..."
        try_step _update_system_packages
        if (( STEP_RC == 0 )); then
            recap_add "System packages: upgraded with $PKG_MANAGER"
        else
            log_err "  system package upgrade failed; continuing"
            recap_add "System packages: upgrade FAILED ($PKG_MANAGER)"
        fi
    fi
fi

# ── Claude Code (upstream installer always fetches latest) ─
if command -v claude &> /dev/null; then
    log_info "Updating Claude Code..."
    try_step _update_claude
    if (( STEP_RC == 0 )); then
        recap_add "Claude Code: refreshed from upstream installer"
    else
        log_err "  Claude Code update failed; continuing"
        recap_add "Claude Code: update FAILED"
    fi
else
    recap_add "Claude Code: skipped (claude not installed)"
fi

# ── Neovim plugins ───────────────────────────────────────
if command -v nvim &> /dev/null; then
    log_info "Syncing Neovim plugins..."
    try_step nvim --headless "+Lazy! sync" +qa
    if (( STEP_RC == 0 )); then
        log_ok "  plugins synced"
        recap_add "Neovim plugins: synced with Lazy"
    else
        log_err "  Neovim plugin sync failed; continuing"
        recap_add "Neovim plugins: sync FAILED"
    fi
else
    recap_add "Neovim plugins: skipped (nvim not installed)"
fi

# ── Language toolchains ──────────────────────────────────
if command -v rustup &> /dev/null; then
    log_info "Updating Rust..."
    try_step rustup update
    if (( STEP_RC == 0 )); then
        recap_add "Rust: updated rustup toolchains"
    else
        log_err "  Rust update failed; continuing"
        recap_add "Rust: update FAILED"
    fi
else
    recap_add "Rust: skipped (rustup not installed)"
fi

if command -v npm &> /dev/null; then
    log_info "Updating npm globals..."
    try_step npm update -g
    if (( STEP_RC == 0 )); then
        recap_add "npm globals: updated"
    else
        log_err "  npm global update failed; continuing"
        recap_add "npm globals: update FAILED"
    fi
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
