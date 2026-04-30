#!/bin/bash
# Claude Code CLI — Anthropic's native installer with pinned SHA256.
# Cross-platform: same install path on macOS and Linux.
# Bump CLAUDE_CODE_INSTALL_SHA256 when upstream releases a new installer:
#   curl -fsSL https://claude.ai/install.sh | shasum -a 256

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

CLAUDE_CODE_INSTALL_SHA256="b315b46925a9bfb9422f2503dd5aa649f680832f4c076b22d87c39d578c3d830"

install_claude_code() {
    if command -v claude &> /dev/null; then
        log_info "Claude Code already installed at $(command -v claude); skipping"
        return 0
    fi
    log_info "Installing Claude Code (native binary)..."
    verify_and_run \
        https://claude.ai/install.sh \
        /tmp/claude-install.sh \
        "$CLAUDE_CODE_INSTALL_SHA256"
}
