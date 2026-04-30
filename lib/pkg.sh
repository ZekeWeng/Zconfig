#!/bin/bash
# Package manager abstraction. Source after lib/common.sh.
#
# After sourcing:
#   $PKG_MANAGER = "apt" | "dnf" | "pacman" | "" (none detected)
# Provides:
#   pkg_install <pkg...>     install one or more packages
#   pkg_update_lists         refresh package metadata
#   pkg_has <pkg>            return 0 if a package is available in the repo

[[ -n "${_ZCONFIG_PKG_LOADED:-}" ]] && return 0
_ZCONFIG_PKG_LOADED=1

if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
else
    PKG_MANAGER=""
fi
export PKG_MANAGER

pkg_install() {
    case "$PKG_MANAGER" in
        apt)    sudo apt-get install -y --no-install-recommends "$@" ;;
        dnf)    sudo dnf install -y "$@" ;;
        pacman) sudo pacman -S --noconfirm "$@" ;;
        *)      log_err "No supported package manager (apt/dnf/pacman)"; return 1 ;;
    esac
}

pkg_update_lists() {
    case "$PKG_MANAGER" in
        apt)    sudo apt-get update ;;
        dnf)    sudo dnf check-update || true ;;
        pacman) sudo pacman -Sy ;;
        *)      log_err "No supported package manager"; return 1 ;;
    esac
}

# Check whether a package is available without installing.
pkg_has() {
    local pkg="$1"
    case "$PKG_MANAGER" in
        apt)    apt-cache show "$pkg" &> /dev/null ;;
        dnf)    dnf info "$pkg" &> /dev/null ;;
        pacman) pacman -Si "$pkg" &> /dev/null ;;
        *)      return 1 ;;
    esac
}
