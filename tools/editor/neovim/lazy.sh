#!/bin/bash
# install_lazy_nvim — clone lazy.nvim plugin manager, pinned to a SHA.
# The SHA lives in init.lua (single source of truth — init.lua has to be
# self-contained so first-launch bootstrap from nvim works); read it here.

[[ -n "${_ZCONFIG_NEOVIM_LAZY_LOADED:-}" ]] && return 0
_ZCONFIG_NEOVIM_LAZY_LOADED=1

LAZY_NVIM_DIR="$HOME/.local/share/nvim/lazy/lazy.nvim"

install_lazy_nvim() {
    [[ -d "$LAZY_NVIM_DIR" ]] && return 0
    local init_lua="${ZCONFIG_DIR}/tools/editor/neovim/config/init.lua"
    local sha
    sha="$(grep -oE 'lazy_sha = "[a-f0-9]{40}"' "$init_lua" | grep -oE '[a-f0-9]{40}')"
    if [[ -z "$sha" ]]; then
        log_err "Could not extract lazy_sha from $init_lua"
        return 1
    fi
    log_info "Installing lazy.nvim (pinned to ${sha:0:7})..."
    git clone --filter=blob:none https://github.com/folke/lazy.nvim.git "$LAZY_NVIM_DIR"
    git -C "$LAZY_NVIM_DIR" checkout "$sha"
}
