#!/bin/bash
# OpenAI Codex CLI — pinned native binary (Linux only). macOS uses brew cask.
# Bump CODEX_VERSION + hashes when upgrading.

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

CODEX_VERSION="rust-v0.124.0"

install_codex() {
    if command -v codex &> /dev/null; then
        log_info "Codex already installed; skipping"
        return 0
    fi
    local binary sha
    case "$ARCH" in
        x86_64)
            binary="codex-x86_64-unknown-linux-gnu"
            sha="0d619d52d24e36c5ed159323d921d8a6709d9ebce375045d043d7a5909fc6b09"
            ;;
        aarch64)
            binary="codex-aarch64-unknown-linux-gnu"
            sha="9765486daac5af97b26864b5d3501d32aa6306b5f9f81b2bd6160b6ca46cb579"
            ;;
        *)
            log_info "Skipping Codex — unsupported arch: $(uname -m)"
            return 0
            ;;
    esac
    local asset="${binary}.tar.gz"

    log_info "Installing OpenAI Codex CLI (${CODEX_VERSION} / ${ARCH})..."
    local tmp="/tmp/${asset}"
    # shellcheck disable=SC2064  # bake paths now; RETURN traps fire in each enclosing frame
    trap "rm -f '$tmp' '/tmp/${binary}'" RETURN
    verify_and_download \
        "https://github.com/openai/codex/releases/download/${CODEX_VERSION}/${asset}" \
        "$tmp" \
        "$sha"
    tar -xzf "$tmp" -C /tmp
    sudo install -m 755 "/tmp/${binary}" /usr/local/bin/codex
}
