#!/bin/bash
# uv (Python package manager) — package manager first, hash-verified upstream installer fallback.
# Bump UV_INSTALL_SHA256 when upstream releases a new installer:
#   curl -fsSL https://astral.sh/uv/install.sh | shasum -a 256

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

UV_INSTALL_SHA256="efed99618cb5c31e4e36a700ab7c3698e83c0ae0f3c336714043d0f932c8d32c"

install_uv() {
    if command -v uv &> /dev/null; then
        log_info "uv already installed; skipping"
        return 0
    fi
    log_info "Installing uv..."
    if pkg_has uv && pkg_install uv; then
        return 0
    fi
    log_info "  uv unavailable via ${PKG_MANAGER} — falling back to pinned upstream installer"
    verify_and_run \
        https://astral.sh/uv/install.sh \
        /tmp/uv-install.sh \
        "$UV_INSTALL_SHA256"
}
