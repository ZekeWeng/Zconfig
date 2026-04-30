#!/bin/bash
# write_gitconfig_local — emit ~/.gitconfig.local from $GIT_USER_NAME /
# $GIT_USER_EMAIL. The committed .gitconfig `[include]`s this file, so user
# identity stays out of the repo.

[[ -n "${_ZCONFIG_GIT_RENDER_LOADED:-}" ]] && return 0
_ZCONFIG_GIT_RENDER_LOADED=1

write_gitconfig_local() {
    [[ -z "${GIT_USER_NAME:-}" && -z "${GIT_USER_EMAIL:-}" ]] && return 0
    # Compare-before-write so user-edited mtimes don't churn on re-runs.
    local rendered
    rendered="$(mktemp)"
    # shellcheck disable=SC2064  # bake the path now; RETURN traps fire in each enclosing frame
    trap "rm -f '$rendered'" RETURN
    {
        echo "[user]"
        [[ -n "${GIT_USER_NAME:-}" ]]  && printf '\tname = %s\n'  "$GIT_USER_NAME"
        [[ -n "${GIT_USER_EMAIL:-}" ]] && printf '\temail = %s\n' "$GIT_USER_EMAIL"
    } > "$rendered"
    if ! cmp -s "$rendered" "$HOME/.gitconfig.local" 2> /dev/null; then
        mv "$rendered" "$HOME/.gitconfig.local"
        log_ok "Wrote ~/.gitconfig.local from .env"
    fi
}
