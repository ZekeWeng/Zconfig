#!/bin/bash
# Shared helpers — sourced by orchestrators and installers.
# Pure: defines functions and sets variables; no side effects beyond exports.

# Idempotency guard so re-sourcing in the same shell is cheap and safe.
[[ -n "${_ZCONFIG_COMMON_LOADED:-}" ]] && return 0
_ZCONFIG_COMMON_LOADED=1

# Color codes (prefixed to avoid clobbering caller variables)
_ZCONFIG_RED=$'\033[0;31m'
_ZCONFIG_GREEN=$'\033[0;32m'
_ZCONFIG_YELLOW=$'\033[1;33m'
_ZCONFIG_NC=$'\033[0m'

# Logging helpers
log_info() { printf '%b%s%b\n' "$_ZCONFIG_YELLOW" "$*" "$_ZCONFIG_NC"; }
log_ok()   { printf '%b%s%b\n' "$_ZCONFIG_GREEN"  "$*" "$_ZCONFIG_NC"; }
log_err()  { printf '%b%s%b\n' "$_ZCONFIG_RED"    "$*" "$_ZCONFIG_NC" >&2; }

# Resolve the dotfiles dir. Set once; respect the env var if a caller pre-sets it.
: "${ZCONFIG_DIR:=$HOME/.zconfig}"
export ZCONFIG_DIR

# Source an installer file. Installers live at tools/<category>/<tool>/install.sh;
# we glob across categories so callers don't need to know the category.
# Installers self-contain their setup; the caller is responsible only for
# sourcing lib/bootstrap.sh first.
load_installer() {
    local name="$1"
    local path
    for path in "$ZCONFIG_DIR"/tools/*/"$name"/install.sh; do
        if [[ -f "$path" ]]; then
            # shellcheck source=/dev/null
            source "$path"
            return 0
        fi
    done
    log_err "Installer not found: $name (searched $ZCONFIG_DIR/tools/*/$name/install.sh)"
    return 1
}

# Run an installer end-to-end: load the file, then call its install_<name> fn.
# Hyphens in installer names map to underscores in function names.
run_installer() {
    local name="$1"; shift || true
    local fn="install_${name//-/_}"
    load_installer "$name"
    if ! declare -F "$fn" > /dev/null; then
        log_err "Installer '$name' is missing function $fn()"
        return 1
    fi
    "$fn" "$@"
}
