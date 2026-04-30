#!/bin/bash
# link_configs — symlink dotfiles into $HOME. Safe against the `ln -sf` directory
# footgun: if $TARGET is an existing real directory, ln -sf silently nests the
# link inside it. We refuse and surface a clear error.
#
# ZCONFIG_SYMLINKS is the single source of truth for what gets symlinked. Both
# link_configs (here) and scripts/backup.sh iterate it.

[[ -n "${_ZCONFIG_BOOTSTRAP_SYMLINKS_LOADED:-}" ]] && return 0
_ZCONFIG_BOOTSTRAP_SYMLINKS_LOADED=1

# Each entry: "<repo-relative-source>::<target-relative-to-$HOME>".
ZCONFIG_SYMLINKS=(
    "tools/editor/neovim/config::.config/nvim"
    "tools/shell/zsh/config/.zshrc::.zshrc"
    "tools/shell/zsh/config/.zshenv::.zshenv"
    "tools/workflow/git/config/.gitconfig::.gitconfig"
    "tools/workflow/git/config/.gitignore_global::.gitignore_global"
    "tools/terminal/tmux/config/.tmux.conf::.tmux.conf"
    "tools/shell/starship/config/starship.toml::.config/starship.toml"
)

# safe_link <src> <tgt>
# - missing tgt:           create symlink
# - tgt is a symlink:      atomic replace via `ln -sfn`
# - tgt is a real file:    overwrite via `ln -sf`
# - tgt is a real dir:     fail loudly — never silently nest
safe_link() {
    local src="$1" tgt="$2"
    if [[ -L "$tgt" ]]; then
        ln -sfn "$src" "$tgt"
    elif [[ -d "$tgt" ]]; then
        log_err "Refusing to link over real directory: $tgt"
        log_err "  Move it aside (e.g. mv $tgt ${tgt}.bak-\$(date +%s)) and re-run."
        return 1
    elif [[ -e "$tgt" ]]; then
        ln -sf "$src" "$tgt"
    else
        ln -s "$src" "$tgt"
    fi
}

link_configs() {
    local d="$1"
    mkdir -p "$HOME/.config" "$HOME/.ssh"
    log_info "Linking configs..."
    local entry src tgt
    for entry in "${ZCONFIG_SYMLINKS[@]}"; do
        src="${entry%%::*}"
        tgt="${entry##*::}"
        mkdir -p "$HOME/$(dirname "$tgt")"
        safe_link "$d/$src" "$HOME/$tgt"
    done
}
