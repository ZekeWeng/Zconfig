#!/bin/bash
# lazygit — pinned native binary (Linux only). macOS uses brew.
# Bump LAZYGIT_VERSION + hashes when upgrading.

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

LAZYGIT_VERSION="v0.62.2"

install_lazygit() {
    if command -v lazygit &> /dev/null; then
        log_info "lazygit already installed; skipping"
        return 0
    fi
    local platform sha
    case "$ARCH" in
        x86_64)
            platform="linux_x86_64"
            sha="8b9a4c2d0969cbea92b45c956dd2a44e1ba76900c9df49f1c60984045ce77984"
            ;;
        aarch64)
            platform="linux_arm64"
            sha="9ab63dd75a7e9711c4c68a37d77f4334b8099a5d6a3f8fbe8f4e2768b159c9e9"
            ;;
        *)
            log_info "Skipping lazygit — unsupported arch: $(uname -m)"
            return 0
            ;;
    esac
    local version_bare="${LAZYGIT_VERSION#v}"
    local asset="lazygit_${version_bare}_${platform}.tar.gz"

    log_info "Installing lazygit ${LAZYGIT_VERSION} (pinned)..."
    local tmp="/tmp/${asset}"
    # shellcheck disable=SC2064  # bake the path now; RETURN traps fire in each enclosing frame
    trap "rm -f '$tmp' /tmp/lazygit" RETURN
    verify_and_download \
        "https://github.com/jesseduffield/lazygit/releases/download/${LAZYGIT_VERSION}/${asset}" \
        "$tmp" \
        "$sha"
    tar xf "$tmp" -C /tmp lazygit
    sudo install /tmp/lazygit /usr/local/bin
}
