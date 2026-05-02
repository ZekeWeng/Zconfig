#!/bin/bash
# starship prompt — pinned native binary (Linux only). macOS uses brew.
# Bump STARSHIP_VERSION + hashes when upgrading:
#   curl -fsSL https://github.com/starship/starship/releases/download/<ver>/starship-<arch>-unknown-linux-musl.tar.gz | shasum -a 256

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

STARSHIP_VERSION="v1.25.1"

install_starship() {
    if command -v starship &> /dev/null; then
        log_info "starship already installed; skipping"
        return 0
    fi
    local triple sha
    case "$ARCH" in
        x86_64)
            triple="x86_64-unknown-linux-musl"
            sha="c6ddd3ecb9c0071a2ad38d98cee748160066b7c4f197421268058f4a5d6f8504"
            ;;
        aarch64)
            triple="aarch64-unknown-linux-musl"
            sha="01517aab398959ea9ea73bdb4f032ea4dbb51dff5c8e5eb05b4a1b9b7ab872b8"
            ;;
        *)
            log_info "Skipping starship — unsupported arch: $(uname -m)"
            return 0
            ;;
    esac
    local asset="starship-${triple}.tar.gz"

    log_info "Installing starship ${STARSHIP_VERSION} (pinned)..."
    local tmp="/tmp/${asset}"
    # shellcheck disable=SC2064  # bake paths now; RETURN traps fire in each enclosing frame
    trap "rm -f '$tmp' /tmp/starship" RETURN
    verify_and_download \
        "https://github.com/starship/starship/releases/download/${STARSHIP_VERSION}/${asset}" \
        "$tmp" \
        "$sha"
    tar -xzf "$tmp" -C /tmp starship
    sudo install -m 755 /tmp/starship /usr/local/bin/starship
}
