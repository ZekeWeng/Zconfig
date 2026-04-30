#!/bin/bash
# SHA256-verified download primitives. Source after lib/common.sh.

[[ -n "${_ZCONFIG_VERIFY_LOADED:-}" ]] && return 0
_ZCONFIG_VERIFY_LOADED=1

# verify_sha256 <file> <expected_hash>
# Compares the file's SHA256 against the expected value. Returns non-zero on mismatch.
verify_sha256() {
    local file="$1" expected="$2" actual
    if command -v sha256sum &> /dev/null; then
        actual="$(sha256sum "$file" | awk '{print $1}')"
    elif command -v shasum &> /dev/null; then
        actual="$(shasum -a 256 "$file" | awk '{print $1}')"
    else
        log_err "No SHA256 tool found (need sha256sum or shasum)"
        return 1
    fi
    if [[ "$actual" != "$expected" ]]; then
        log_err "Checksum mismatch for ${file}"
        log_err "  expected: ${expected}"
        log_err "  actual:   ${actual}"
        return 1
    fi
}

# verify_and_download <url> <dest_path> <expected_hash>
# Downloads to dest_path and verifies. Removes dest on mismatch.
verify_and_download() {
    local url="$1" dest="$2" expected="$3"
    curl -fsSL "$url" -o "$dest" || { log_err "Download failed: $url"; return 1; }
    if ! verify_sha256 "$dest" "$expected"; then
        rm -f "$dest"
        return 1
    fi
}

# verify_and_run <url> <tmp_path> <expected_hash> [args...]
# Downloads, verifies, executes via bash with optional extra args, then cleans up.
verify_and_run() {
    local url="$1" path="$2" expected="$3"
    shift 3
    verify_and_download "$url" "$path" "$expected" || return 1
    bash "$path" "$@"
    local rc=$?
    rm -f "$path"
    return $rc
}
