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

# Ensure the Xcode Command Line Tools (git, compilers, make) are present —
# Homebrew and any formula that builds from source need them. `xcode-select
# --install` returns immediately and pops a GUI installer, so block until the
# tools land. Almost always a no-op: cloning this repo already required git.
ensure_xcode_clt() {
    xcode-select -p &> /dev/null && return 0
    log_info "Installing Xcode Command Line Tools..."
    xcode-select --install &> /dev/null || true
    # Wait for the GUI installer to finish, but fail fast instead of hanging
    # forever if it is cancelled, stalls, or there is no GUI to answer it.
    local waited=0
    until xcode-select -p &> /dev/null; do
        if (( waited >= 1800 )); then
            log_err "Xcode Command Line Tools still missing after 30m."
            log_err "Finish 'xcode-select --install', then re-run."
            exit 1
        fi
        sleep 5
        waited=$(( waited + 5 ))
    done
    log_ok "Xcode Command Line Tools installed."
}

# Ensure Homebrew is installed and on PATH for the rest of this process. brew
# lands outside the default PATH on Apple Silicon (/opt/homebrew), so eval its
# shellenv after a fresh install.
ensure_homebrew() {
    command -v brew &> /dev/null && return 0
    log_info "Installing Homebrew..."
    local installer
    installer="$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" \
        || { log_err "Could not download the Homebrew installer (check your network)"; exit 1; }
    NONINTERACTIVE=1 /bin/bash -c "$installer"
    if [[ -x /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    command -v brew &> /dev/null || { log_err "Homebrew installation failed"; exit 1; }
}

INSTALL_BREW=true
for arg in "$@"; do
    case "$arg" in
        --no-brew) INSTALL_BREW=false ;;
        *)         ;;
    esac
done

log_info "macOS installation"

ensure_xcode_clt

if [[ "$INSTALL_BREW" == true ]]; then
    ensure_homebrew
    log_info "Installing Homebrew packages..."
    brew bundle --file="$ZCONFIG_DIR/platform/mac/Brewfile"
    # Machine-local additions — gitignored, same pattern as ~/.zshrc.local.
    if [[ -f "$ZCONFIG_DIR/platform/mac/Brewfile.local" ]]; then
        log_info "Installing local Homebrew packages (Brewfile.local)..."
        brew bundle --file="$ZCONFIG_DIR/platform/mac/Brewfile.local"
    fi
else
    log_info "Skipping Homebrew package installation (--no-brew flag)"
fi

# Direct-download installers (avoid brew cask flakiness for these tools)
run_installer vscode
run_installer claude-code

log_ok "macOS installation complete."
