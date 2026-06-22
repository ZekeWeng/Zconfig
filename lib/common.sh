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

# Optional installers — non-critical tools (editors, fonts, AI CLIs). A failure
# (usually a flaky download) is recorded and reported at the end, never fatal:
# one bad fetch must not abort the whole install and skip everything after it.
# Critical base steps (essentials, Homebrew) stay fatal — no point continuing
# without them. The subshell re-enables `set -e` so the installer still fails
# fast internally, while the `if` keeps that failure from aborting the caller.
_ZCONFIG_FAILED_INSTALLERS=()

run_optional_installer() {
    local name="$1"; shift || true
    # Disable -e in the caller so a failure here can't abort the run, but keep -e
    # ON inside the subshell so the installer still stops at its first failed step.
    # Testing the subshell with `if`/`||` would re-suppress -e *inside* it, so run
    # it as a standalone statement and capture $? on the very next line.
    local rc=0
    set +e
    ( set -e; run_installer "$name" "$@" )
    rc=$?
    set -e
    if (( rc != 0 )); then
        log_err "  ${name} failed — continuing (re-run 'make install' to retry)"
        _ZCONFIG_FAILED_INSTALLERS+=("$name")
    fi
}

report_optional_failures() {
    (( ${#_ZCONFIG_FAILED_INSTALLERS[@]} == 0 )) && return 0
    log_err "Some optional installers failed and were skipped:"
    printf '  - %s\n' "${_ZCONFIG_FAILED_INSTALLERS[@]}" >&2
    log_err "Re-run 'make install' to retry (already-installed tools are skipped)."
}
