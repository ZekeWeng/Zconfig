#!/bin/bash
# starship prompt — package manager first, hash-verified upstream installer fallback.
# Bump STARSHIP_INSTALL_SHA256 when upstream releases a new installer:
#   curl -fsSL https://starship.rs/install.sh | shasum -a 256

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

STARSHIP_INSTALL_SHA256="52c64f14a558034ebeb1907ea9364e802b32474576fd3e68265f73bc33cc8fbb"

install_starship() {
    if command -v starship &> /dev/null; then
        log_info "starship already installed; skipping"
        return 0
    fi
    log_info "Installing starship..."
    if pkg_has starship && pkg_install starship; then
        return 0
    fi
    log_info "  starship unavailable via ${PKG_MANAGER} — falling back to pinned upstream installer"
    verify_and_run \
        https://starship.rs/install.sh \
        /tmp/starship-install.sh \
        "$STARSHIP_INSTALL_SHA256" \
        -- -y
}
