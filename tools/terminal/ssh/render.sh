#!/bin/bash
# bootstrap_ssh — generate an SSH key (if absent) and write ~/.ssh/config from
# the template, substituting the user's chosen key name. Reads $SSH_KEY_NAME
# and $GIT_USER_EMAIL from the environment (loaded from .env).

[[ -n "${_ZCONFIG_SSH_RENDER_LOADED:-}" ]] && return 0
_ZCONFIG_SSH_RENDER_LOADED=1

bootstrap_ssh() {
    local zconfig_dir="$1"
    local key="${SSH_KEY_NAME:-id_ed25519}"

    if [[ ! "$key" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        log_err "Invalid SSH_KEY_NAME in .env — must be alphanumeric/hyphens/underscores only"
        return 1
    fi

    # Seed config.local once so users have somewhere to add machine-specific hosts.
    if [[ ! -f "$HOME/.ssh/config.local" ]]; then
        cp "$zconfig_dir/tools/terminal/ssh/config/config.local.example" "$HOME/.ssh/config.local"
        log_info "Created ~/.ssh/config.local — add machine-specific hosts there"
    fi

    if [[ ! -f "$HOME/.ssh/$key" ]]; then
        local email="${GIT_USER_EMAIL:-$USER@$(hostname)}"
        log_info "Generating SSH key (ed25519)..."
        ssh-keygen -t ed25519 -C "$email" -f "$HOME/.ssh/$key"
        log_ok "SSH key generated. Add it to GitHub:"
        log_info "  cat ~/.ssh/${key}.pub"
        log_info "  Then paste at: https://github.com/settings/ssh/new"
    fi

    # Compare-before-write so user-edited mtimes don't churn on re-runs and
    # any divergence (a manually-edited config) is surfaced as a real change.
    local rendered
    rendered="$(mktemp)"
    # shellcheck disable=SC2064  # bake the path now; RETURN traps fire in each enclosing frame
    trap "rm -f '$rendered'" RETURN
    sed "s|~/.ssh/id_ed25519|~/.ssh/${key}|g" \
        "$zconfig_dir/tools/terminal/ssh/config/config" > "$rendered"
    if ! cmp -s "$rendered" "$HOME/.ssh/config" 2> /dev/null; then
        mv "$rendered" "$HOME/.ssh/config"
        log_ok "Wrote ~/.ssh/config (key: $key)"
    fi
    chmod 600 "$HOME/.ssh/config"
}
