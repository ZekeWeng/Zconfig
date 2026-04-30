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

# Steps that only touch $HOME — safe in any environment, no downloads.
ensure_env_file       "$ZCONFIG_DIR"
load_env              "$ZCONFIG_DIR/.env"
link_configs          "$ZCONFIG_DIR"
bootstrap_ssh         "$ZCONFIG_DIR"
write_gitconfig_local

# Corp profile stops here: configs are linked, identity files written, no
# downloads, no sudo, no GitHub clones, no package installs. Set via env
# var or .env (ZCONFIG_PROFILE=corp).
if [[ "${ZCONFIG_PROFILE:-full}" == "corp" ]]; then
    log_ok "Corp profile — skipped tool installers, brew bundle, lazy.nvim, pre-commit hooks."
    log_info "Restart your terminal or run: exec zsh"
    exit 0
fi

# Full profile: download/install tooling.
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
