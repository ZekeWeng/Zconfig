#!/bin/bash
# uv (Python package manager) — pinned native binary (Linux only). macOS uses brew.
# Bump UV_VERSION + hashes when upgrading:
#   curl -fsSL https://github.com/astral-sh/uv/releases/download/<ver>/uv-<arch>-unknown-linux-gnu.tar.gz | shasum -a 256

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

UV_VERSION="0.11.8"

install_uv() {
    if command -v uv &> /dev/null; then
        log_info "uv already installed; skipping"
        return 0
    fi
    local triple sha
    case "$ARCH" in
        x86_64)
            triple="x86_64-unknown-linux-gnu"
            sha="56dd1b66701ecb62fe896abb919444e4b83c5e8645cca953e6ddd496ff8a0feb"
            ;;
        aarch64)
            triple="aarch64-unknown-linux-gnu"
            sha="eee8dd658d20e5ac85fec9c2326b6cbc9d83a1eef09ef07433e58698ac849591"
            ;;
        *)
            log_info "Skipping uv — unsupported arch: $(uname -m)"
            return 0
            ;;
    esac
    local extract_dir="uv-${triple}"
    local asset="${extract_dir}.tar.gz"

    log_info "Installing uv ${UV_VERSION} (pinned)..."
    local tmp="/tmp/${asset}"
    # shellcheck disable=SC2064  # bake paths now; RETURN traps fire in each enclosing frame
    trap "rm -rf '$tmp' '/tmp/${extract_dir}'" RETURN
    verify_and_download \
        "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${asset}" \
        "$tmp" \
        "$sha"
    tar -xzf "$tmp" -C /tmp
    sudo install -m 755 "/tmp/${extract_dir}/uv" /usr/local/bin/uv
    sudo install -m 755 "/tmp/${extract_dir}/uvx" /usr/local/bin/uvx
}
