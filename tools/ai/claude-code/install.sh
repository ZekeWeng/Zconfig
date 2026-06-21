#!/bin/bash
# Claude Code CLI — Anthropic's official installer.
# Cross-platform: same install path on macOS and Linux.
#
# We do NOT pin a hash of install.sh: Anthropic ships it several times a week,
# so a pinned wrapper hash breaks installs constantly. It also adds nothing —
# the installer downloads each release's manifest.json and verifies the binary
# against the SHA256 it lists before running it, so binary integrity is already
# guaranteed upstream. We pin the release *channel* instead for reproducibility.
#   CLAUDE_CODE_CHANNEL=stable|latest|X.Y.Z   (default: stable)

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

CLAUDE_CODE_CHANNEL="${CLAUDE_CODE_CHANNEL:-stable}"

install_claude_code() {
    if command -v claude &> /dev/null; then
        log_info "Claude Code already installed at $(command -v claude); skipping"
        return 0
    fi
    log_info "Installing Claude Code (${CLAUDE_CODE_CHANNEL}) via Anthropic's official installer..."
    local installer
    installer="$(mktemp)" || { log_err "Failed to create a temp file for the installer"; return 1; }
    # shellcheck disable=SC2064  # bake the path now; RETURN traps fire in each enclosing frame
    trap "rm -f '$installer'" RETURN
    curl -fsSL https://claude.ai/install.sh -o "$installer" \
        || { log_err "Failed to download the Claude Code installer"; return 1; }
    bash "$installer" "$CLAUDE_CODE_CHANNEL"
}
