#!/bin/bash
# eza — modern ls. dnf and pacman ship it directly; apt needs the gierens repo.

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

install_eza() {
    if command -v eza &> /dev/null; then
        log_info "eza already installed; skipping"
        return 0
    fi
    log_info "Installing eza..."
    case "$PKG_MANAGER" in
        apt)
            sudo install -d -m 0755 /etc/apt/keyrings
            curl -fsSL https://raw.githubusercontent.com/eza-community/eza/main/deb.asc \
                | sudo gpg --dearmor -o /etc/apt/keyrings/gierens.gpg
            echo "deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main" \
                | sudo tee /etc/apt/sources.list.d/gierens.list > /dev/null
            sudo apt-get update
            pkg_install eza
            ;;
        dnf|pacman)
            pkg_install eza
            ;;
        *)
            log_err "eza: unsupported package manager"
            return 1
            ;;
    esac
}
