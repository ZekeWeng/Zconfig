#!/bin/bash
# Linux base packages — git, zsh, tmux, fzf, and friends.
# Reconciles distro-specific binary names (fdfind/fd).

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

install_essentials() {
    local missing=()
    local cmd
    for cmd in git zsh tmux fzf rg fd shellcheck; do
        command -v "$cmd" &> /dev/null || missing+=("$cmd")
    done
    if (( ${#missing[@]} == 0 )); then
        log_info "essentials already installed; skipping"
        return 0
    fi
    log_info "Installing essential packages (missing: ${missing[*]})..."
    case "$PKG_MANAGER" in
        apt)
            pkg_install \
                git zsh tmux fzf ripgrep fd-find shellcheck \
                python3 python3-pip python3-venv \
                xclip curl wget unzip fontconfig
            # Debian/Ubuntu rename the binaries — symlink to the canonical names.
            if ! command -v fd &> /dev/null && command -v fdfind &> /dev/null; then
                sudo ln -sf "$(command -v fdfind)" /usr/local/bin/fd
            fi
            ;;
        dnf)
            pkg_install \
                git zsh tmux fzf ripgrep fd-find ShellCheck \
                python3 python3-pip \
                xclip curl wget unzip fontconfig
            ;;
        pacman)
            pkg_install \
                git zsh tmux fzf ripgrep fd shellcheck \
                python python-pip \
                xclip curl wget unzip fontconfig
            ;;
        *)
            log_err "essentials: unsupported package manager"
            return 1
            ;;
    esac
}
