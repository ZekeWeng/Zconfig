#!/bin/bash
# OpenAI Codex CLI — pinned native binary (Linux only). macOS uses brew cask.
# Upstream ships statically-linked musl builds (the gnu target was dropped).
# Bump CODEX_VERSION + hashes when upgrading.

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

CODEX_VERSION="rust-v0.141.0"

install_codex() {
    if command -v codex &> /dev/null; then
        log_info "Codex already installed; skipping"
        return 0
    fi
    local binary sha
    case "$ARCH" in
        x86_64)
            binary="codex-x86_64-unknown-linux-musl"
            sha="f1e2bf9fa0ba6eb82119d621b6b71bc38edd33c06dc2867b31a027052358957d"
            ;;
        aarch64)
            binary="codex-aarch64-unknown-linux-musl"
            sha="8c9f31811d659fcc17c5f1a21bc0971984469c9e3a63c2b39b61cc7694f3a101"
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
