#!/bin/bash
# ensure_env_file — bootstrap .env from .env.example on first install.
# The runtime parser (load_env) lives in lib/env.sh.

[[ -n "${_ZCONFIG_BOOTSTRAP_ENV_LOADED:-}" ]] && return 0
_ZCONFIG_BOOTSTRAP_ENV_LOADED=1

ensure_env_file() {
    local zconfig_dir="$1"
    if [[ ! -f "$zconfig_dir/.env" ]]; then
        cp "$zconfig_dir/.env.example" "$zconfig_dir/.env"
        chmod 600 "$zconfig_dir/.env"  # may hold API tokens — keep it owner-only
        log_info "Created .env from .env.example — edit $zconfig_dir/.env with your values"
        prompt_identity "$zconfig_dir/.env"
    fi
}

# env_file_set <file> <key> <value> — replace a key's line in a .env file.
# Quotes the value when it contains '#' so load_env keeps it verbatim.
env_file_set() {
    local file="$1" key="$2" value="$3" tmp line
    [[ "$value" == *'#'* ]] && value="\"$value\""
    tmp="$(mktemp)"
    while IFS= read -r line; do
        if [[ "$line" == "$key="* ]]; then
            printf '%s=%s\n' "$key" "$value"
        else
            printf '%s\n' "$line"
        fi
    done < "$file" > "$tmp"
    mv "$tmp" "$file"
}

# prompt_identity <env-file>
# Ask for git identity on first install so placeholders never reach
# ~/.gitconfig.local. Reads /dev/tty directly so it works under
# `curl | bash`; silently skips when no terminal is attached (CI).
prompt_identity() {
    local env_file="$1" name email
    ( : < /dev/tty ) 2> /dev/null || return 0
    log_info "Set your git identity (stored in .env, never committed; enter to skip):"
    printf 'Git user name: ' > /dev/tty
    IFS= read -r name < /dev/tty || name=""
    printf 'Git email: ' > /dev/tty
    IFS= read -r email < /dev/tty || email=""
    [[ -n "$name" ]]  && env_file_set "$env_file" GIT_USER_NAME "$name"
    [[ -n "$email" ]] && env_file_set "$env_file" GIT_USER_EMAIL "$email"
    return 0
}
