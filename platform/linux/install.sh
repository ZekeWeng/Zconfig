#!/bin/bash
# Linux orchestrator — sources the lib layer, then runs each installer in order.
# Adding a tool: add tools/<category>/<name>/install.sh and a run_installer line below.

set -euo pipefail
IFS=$'\n\t'

if [[ "$(uname)" != "Linux" ]]; then
    echo "This script is for Linux." >&2
    exit 1
fi

export ZCONFIG_DIR="${ZCONFIG_DIR:-$HOME/.zconfig}"

# shellcheck source=../../lib/bootstrap.sh
source "$ZCONFIG_DIR/lib/bootstrap.sh"

if [[ -z "$PKG_MANAGER" ]]; then
    log_err "No supported package manager (apt/dnf/pacman)."
    exit 1
fi
log_info "Linux installation — package manager: ${PKG_MANAGER}"
pkg_update_lists

# Install order: base packages → distro repos → tools → fonts → AI CLIs
run_installer essentials
run_installer neovim
run_installer eza
run_installer lazygit
run_installer gh
run_installer vscode
run_installer starship
run_installer uv
run_installer tree-sitter
run_installer nerd-fonts
run_installer claude-code
run_installer codex

# Set zsh as the login shell if it isn't already. chsh requires PAM auth on
# most distros, which fails for passwordless users (CI runners, container
# images). Treat failure as non-fatal and surface manual instructions.
if [[ "$SHELL" != "$(command -v zsh)" ]]; then
    log_info "Setting zsh as default shell..."
    if ! chsh -s "$(command -v zsh)"; then
        log_info "  chsh failed (likely no interactive auth available)."
        log_info "  Run manually when ready: chsh -s \$(command -v zsh)"
    fi
fi

log_ok "Linux installation complete."
log_info "Run 'exec zsh -l' or restart your terminal to apply changes."
