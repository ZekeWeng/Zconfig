#!/bin/bash
# Neovim — pinned AppImage (Linux only). macOS uses brew.
# Bump NVIM_VERSION + hashes when upgrading.

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

NVIM_VERSION="v0.12.2"
NVIM_MIN_VERSION="0.9.0"

install_neovim() {
    local asset sha
    case "$ARCH" in
        x86_64)
            asset="nvim-linux-x86_64.appimage"
            sha="f9f1901144dc1b0715a1f5178b596d7cdbb22c0f027383bb430862d59377b59f"
            ;;
        aarch64)
            asset="nvim-linux-arm64.appimage"
            sha="ea5bbff4a53176e7677feb59e4246111cadd9eff1ff49613da71ed725a936dcd"
            ;;
        *)
            log_info "Skipping Neovim — unsupported arch: $(uname -m)"
            return 0
            ;;
    esac

    # Skip if a recent enough nvim is already on PATH
    if command -v nvim &> /dev/null; then
        local current
        current="$(nvim --version | head -1 | grep -oP '\d+\.\d+\.\d+')"
        if [[ "$(printf '%s\n%s\n' "$NVIM_MIN_VERSION" "$current" | sort -V | head -1)" == "$NVIM_MIN_VERSION" ]]; then
            log_info "Neovim ${current} already installed; skipping"
            return 0
        fi
    fi

    log_info "Installing Neovim ${NVIM_VERSION} via AppImage (pinned)..."
    # Remove a distro-managed neovim that would conflict on PATH.
    [[ "$PKG_MANAGER" == "apt" ]] && sudo apt-get remove -y neovim &> /dev/null || true

    local tmp="/tmp/${asset}"
    verify_and_download \
        "https://github.com/neovim/neovim/releases/download/${NVIM_VERSION}/${asset}" \
        "$tmp" \
        "$sha"
    chmod u+x "$tmp"
    sudo mv "$tmp" /usr/local/bin/nvim
}
