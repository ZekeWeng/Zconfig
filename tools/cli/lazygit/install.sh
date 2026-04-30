#!/bin/bash
# lazygit — pinned native binary (Linux only). macOS uses brew.
# Bump LAZYGIT_VERSION + hashes when upgrading.

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

LAZYGIT_VERSION="v0.61.1"

install_lazygit() {
    if command -v lazygit &> /dev/null; then
        log_info "lazygit already installed; skipping"
        return 0
    fi
    local platform sha
    case "$ARCH" in
        x86_64)
            platform="Linux_x86_64"
            sha="1b91e660700f2332696726b635202576b543e2bc49b639830dccd26bc5160d5d"
            ;;
        aarch64)
            platform="Linux_arm64"
            sha="20b1abb2bee5dfd46173b9047353eb678bc51a23839e821958d0b1863ab1655e"
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
