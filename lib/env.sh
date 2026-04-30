#!/bin/bash
# load_env <file>
# Safe key=value parser — never executes file contents.
# Lives in lib/ because both install.sh and zsh/.zshenv call it; bootstrap/
# is install-time orchestration only.

[[ -n "${_ZCONFIG_ENV_LOADED:-}" ]] && return 0
_ZCONFIG_ENV_LOADED=1

load_env() {
    [[ -f "$1" ]] || return 1
    while IFS='=' read -r key value; do
        key="${key%%#*}"
        key="${key// /}"
        [[ -z "$key" ]] && continue
        # Trim leading whitespace before deciding whether the value is quoted.
        value="${value#"${value%%[![:space:]]*}"}"
        if [[ "$value" == \"*\" || "$value" == \'*\' ]]; then
            # Quoted — keep contents verbatim (including any '#').
            value="${value:1:${#value}-2}"
        else
            # Unquoted — strip trailing '# comment' and surrounding whitespace.
            value="${value%%#*}"
            value="${value%"${value##*[![:space:]]}"}"
        fi
        export "$key=$value"
    done < "$1"
}
