#!/bin/bash
# install_precommit_hooks — install the `pre-commit` tool via uv and activate
# the .git/hooks shim for this repo. Idempotent: re-running is a no-op.

[[ -n "${_ZCONFIG_PRECOMMIT_LOADED:-}" ]] && return 0
_ZCONFIG_PRECOMMIT_LOADED=1

# Resolve a binary that may live on $PATH or in ~/.local/bin (uv's default).
# Prints the absolute path on stdout, returns nonzero if not found.
_precommit_resolve_bin() {
    local name="$1"
    if command -v "$name" &> /dev/null; then
        command -v "$name"
        return 0
    fi
    local candidate="$HOME/.local/bin/$name"
    [[ -x "$candidate" ]] && { printf '%s\n' "$candidate"; return 0; }
    return 1
}

install_precommit_hooks() {
    local zconfig_dir="${1:-$ZCONFIG_DIR}"
    local uv_bin pre_commit_bin

    if ! uv_bin="$(_precommit_resolve_bin uv)"; then
        log_err "uv not found — skipping pre-commit hook setup. Restart your shell and run: pre-commit install"
        return 0
    fi

    log_info "Installing pre-commit via uv..."
    if ! "$uv_bin" tool install --quiet pre-commit; then
        log_err "Failed to install pre-commit via uv"
        return 0
    fi

    if ! pre_commit_bin="$(_precommit_resolve_bin pre-commit)"; then
        log_err "pre-commit not found after install — check that ~/.local/bin is on PATH"
        return 0
    fi

    log_info "Activating pre-commit git hooks..."
    (cd "$zconfig_dir" && "$pre_commit_bin" install)
}
