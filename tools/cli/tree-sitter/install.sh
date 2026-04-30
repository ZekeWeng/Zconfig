#!/bin/bash
# tree-sitter CLI — required by nvim-treesitter `main` branch (nvim 0.12+).
# Distro pkg where available; otherwise no-op with a hint, since highlight
# falls back gracefully (autocmds.lua wraps treesitter.start in pcall).

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

install_tree_sitter() {
    if command -v tree-sitter &> /dev/null; then
        log_info "tree-sitter already installed; skipping"
        return 0
    fi
    if pkg_has tree-sitter-cli; then
        log_info "Installing tree-sitter CLI..."
        pkg_install tree-sitter-cli
        return 0
    fi
    log_info "tree-sitter-cli unavailable via ${PKG_MANAGER} — install manually for nvim-treesitter parser builds"
}
