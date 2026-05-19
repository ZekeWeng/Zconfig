#!/bin/bash
# link_configs — symlink dotfiles into $HOME. Safe against the `ln -sf` directory
# footgun: if $TARGET is an existing real directory, ln -sf silently nests the
# link inside it. We refuse and surface a clear error.
#
# Two symlink sets:
#   ZCONFIG_SYMLINKS_CORP — terminal styling (zsh + starship + tmux)
#   ZCONFIG_SYMLINKS      — full set (corp + editor + git)
# scripts/backup.sh iterates the full set so backups stay comprehensive.

[[ -n "${_ZCONFIG_BOOTSTRAP_SYMLINKS_LOADED:-}" ]] && return 0
_ZCONFIG_BOOTSTRAP_SYMLINKS_LOADED=1

# Each entry: "<repo-relative-source>::<target-relative-to-$HOME>".
ZCONFIG_SYMLINKS_CORP=(
    "tools/shell/zsh/config/.zshrc::.zshrc"
    "tools/shell/zsh/config/.zshenv::.zshenv"
    "tools/shell/starship/config/starship.toml::.config/starship.toml"
    "tools/terminal/tmux/config/.tmux.conf::.tmux.conf"
)

ZCONFIG_SYMLINKS=(
    "${ZCONFIG_SYMLINKS_CORP[@]}"
    "tools/editor/neovim/config::.config/nvim"
    "tools/workflow/git/config/.gitconfig::.gitconfig"
    "tools/workflow/git/config/.gitignore_global::.gitignore_global"
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
    local d="$1"; shift
    local entries=("$@")
    (( ${#entries[@]} == 0 )) && entries=("${ZCONFIG_SYMLINKS[@]}")
    mkdir -p "$HOME/.config"
    log_info "Linking configs..."
    local entry src tgt
    for entry in "${entries[@]}"; do
        src="${entry%%::*}"
        tgt="${entry##*::}"
        mkdir -p "$HOME/$(dirname "$tgt")"
        safe_link "$d/$src" "$HOME/$tgt"
    done
}
