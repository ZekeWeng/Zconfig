#!/bin/bash
# GitHub CLI — apt via the github.com signed repo; dnf/pacman ship it.

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

install_gh() {
    if command -v gh &> /dev/null; then
        log_info "GitHub CLI already installed; skipping"
        return 0
    fi
    log_info "Installing GitHub CLI..."
    case "$PKG_MANAGER" in
        apt)
            curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
                | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg status=none
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
                | sudo tee /etc/apt/sources.list.d/github-cli-stable.list > /dev/null
            sudo apt-get update
            pkg_install gh
            ;;
        dnf)
            pkg_install gh
            ;;
        pacman)
            pkg_install github-cli
            ;;
        *)
            log_err "gh: unsupported package manager"
            return 1
            ;;
    esac
}
