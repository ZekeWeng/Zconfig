#!/bin/bash
# macOS orchestrator — runs `brew bundle` for everything in the Brewfile,
# then invokes per-tool installers for things that don't ship via brew.

set -euo pipefail
IFS=$'\n\t'

if [[ "$(uname)" != "Darwin" ]]; then
    echo "This script is for macOS." >&2
    exit 1
fi

export ZCONFIG_DIR="${ZCONFIG_DIR:-$HOME/.zconfig}"

# shellcheck source=../../lib/bootstrap.sh
source "$ZCONFIG_DIR/lib/bootstrap.sh"

# Parse arguments
INSTALL_BREW=true
for arg in "$@"; do
    case "$arg" in
        --no-brew) INSTALL_BREW=false ;;
        *)         ;;
    esac
done

log_info "macOS installation"

if [[ "$INSTALL_BREW" == true ]]; then
    if command -v brew &> /dev/null; then
        log_info "Installing Homebrew packages..."
        brew bundle --file="$ZCONFIG_DIR/platform/mac/Brewfile"
    else
        log_err "Homebrew not found. Install Homebrew first: https://brew.sh"
        exit 1
    fi
else
    log_info "Skipping Homebrew package installation (--no-brew flag)"
fi

# Direct-download installers (avoid brew cask flakiness for these tools)
run_installer vscode
run_installer claude-code

log_ok "macOS installation complete."
