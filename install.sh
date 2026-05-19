#!/bin/bash
# Composition root. Reads top-down as a numbered list of steps.
# Cross-cutting bootstrap lives in bootstrap/; tool-specific setup lives next
# to its tool under tools/<category>/<tool>/.

set -euo pipefail
IFS=$'\n\t'

export ZCONFIG_DIR="${ZCONFIG_DIR:-$HOME/.zconfig}"

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

# Corp profile: zsh config only. No starship, no tmux, no SSH key, no
# gitconfig identity, no downloads, no sudo, no package installs.
# Set via env var or .env (ZCONFIG_PROFILE=corp).
if [[ "${ZCONFIG_PROFILE:-full}" == "corp" ]]; then
    link_configs "$ZCONFIG_DIR" "${ZCONFIG_SYMLINKS_CORP[@]}"
    log_ok "Corp profile — linked zsh config only."
    log_info "Restart your terminal or run: exec zsh"
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
