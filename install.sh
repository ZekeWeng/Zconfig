#!/bin/bash
# Composition root. Reads top-down as a numbered list of steps.
# Cross-cutting bootstrap lives in bootstrap/; tool-specific setup lives next
# to its tool under tools/<category>/<tool>/.

set -euo pipefail
IFS=$'\n\t'

# Self-locate so `./install.sh` works from any clone path. The runtime configs
# (.zshrc, .zshenv) hard-reference ~/.zconfig, so ensure that symlink exists.
_SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ZCONFIG_DIR="${ZCONFIG_DIR:-$_SELF_DIR}"

if [[ ! -e "$HOME/.zconfig" ]]; then
    ln -s "$ZCONFIG_DIR" "$HOME/.zconfig"
elif [[ -L "$HOME/.zconfig" && "$(readlink "$HOME/.zconfig")" != "$ZCONFIG_DIR" ]]; then
    echo "warning: ~/.zconfig points to $(readlink "$HOME/.zconfig"), not $ZCONFIG_DIR" >&2
    echo "         runtime configs reference ~/.zconfig — fix this or runtime will break." >&2
elif [[ ! -L "$HOME/.zconfig" && "$HOME/.zconfig" != "$ZCONFIG_DIR" ]]; then
    echo "warning: ~/.zconfig is a real dir at a different location than $ZCONFIG_DIR" >&2
    echo "         runtime configs reference ~/.zconfig — resolve before proceeding." >&2
fi

source "$ZCONFIG_DIR/lib/common.sh"
source "$ZCONFIG_DIR/lib/env.sh"
source "$ZCONFIG_DIR/bootstrap/env.sh"
source "$ZCONFIG_DIR/bootstrap/symlinks.sh"
source "$ZCONFIG_DIR/tools/terminal/ssh/render.sh"
source "$ZCONFIG_DIR/tools/workflow/git/render.sh"
source "$ZCONFIG_DIR/tools/editor/neovim/lazy.sh"
source "$ZCONFIG_DIR/tools/workflow/precommit/install.sh"

log_info "Starting dotfiles installation..."

ensure_env_file       "$ZCONFIG_DIR"
load_env              "$ZCONFIG_DIR/.env"

# Treat untouched .env.example placeholders as unset so we never bake
# "Name <email@example.com>" into ~/.gitconfig.local or the SSH key.
[[ "${GIT_USER_NAME:-}" == "Name" ]] && unset GIT_USER_NAME
[[ "${GIT_USER_EMAIL:-}" == "email@example.com" ]] && unset GIT_USER_EMAIL
if [[ -z "${GIT_USER_NAME:-}" && -z "${GIT_USER_EMAIL:-}" ]]; then
    log_info "Git identity not set — edit $ZCONFIG_DIR/.env and re-run to render ~/.gitconfig.local"
fi

# Corp profile: terminal styling (zsh + starship + tmux) + a lean brew bundle
# (essentials + fonts, no languages/DB/AI casks). No SSH key, no gitconfig
# identity, no VSCode/Claude Code direct downloads, no lazy.nvim, no pre-commit.
# On Linux, runs symlinks only (apt/dnf/pacman would need sudo).
# Set via env var or .env (ZCONFIG_PROFILE=corp).
if [[ "${ZCONFIG_PROFILE:-full}" == "corp" ]]; then
    link_configs "$ZCONFIG_DIR" "${ZCONFIG_SYMLINKS_CORP[@]}"
    if [[ "$(uname)" == "Darwin" ]] && command -v brew &> /dev/null; then
        log_info "Installing corp Homebrew packages..."
        brew bundle --file="$ZCONFIG_DIR/platform/mac/Brewfile.corp"
    fi
    log_ok "Corp profile — terminal styling linked."
    log_info "Restart your terminal or run: exec zsh"
    log_info "Set your terminal font to 'JetBrainsMono Nerd Font' for best appearance"
    exit 0
fi

# Full profile: full symlink set + identity + downloads.
link_configs          "$ZCONFIG_DIR"
bootstrap_ssh         "$ZCONFIG_DIR"
write_gitconfig_local
install_lazy_nvim

case "$(uname)" in
    Darwin) bash "$ZCONFIG_DIR/platform/mac/install.sh"   "$@" ;;
    Linux)  bash "$ZCONFIG_DIR/platform/linux/install.sh" "$@" ;;
    *)      log_err "Unsupported OS: $(uname)"; exit 1 ;;
esac

# Pre-commit hooks: runs after the platform install so `uv` is on disk.
install_precommit_hooks "$ZCONFIG_DIR"

log_ok "Installation complete!"
log_info "Restart your terminal or run: exec zsh"
log_info "Set your terminal font to 'JetBrainsMono Nerd Font' for best appearance"
