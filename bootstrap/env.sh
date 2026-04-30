#!/bin/bash
# ensure_env_file — bootstrap .env from .env.example on first install.
# The runtime parser (load_env) lives in lib/env.sh.

[[ -n "${_ZCONFIG_BOOTSTRAP_ENV_LOADED:-}" ]] && return 0
_ZCONFIG_BOOTSTRAP_ENV_LOADED=1

ensure_env_file() {
    local zconfig_dir="$1"
    if [[ ! -f "$zconfig_dir/.env" ]]; then
        cp "$zconfig_dir/.env.example" "$zconfig_dir/.env"
        log_info "Created .env from .env.example — edit $zconfig_dir/.env with your values"
    fi
}
