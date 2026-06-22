# Interactive-shell configuration. Read top-down.
# Heavier prompt/PATH bootstrap lives in .zshenv.

# ── Modules ──────────────────────────────────────────────
# Each module is a single-purpose file in ~/.zconfig/tools/shell/zsh/config/.
_zconfig_modules=(path aliases functions)
[[ "$OSTYPE" == linux* ]] && _zconfig_modules+=(linux)  # $OSTYPE: no uname fork
for m in "${_zconfig_modules[@]}"; do
    [[ -f ~/.zconfig/tools/shell/zsh/config/${m}.zsh ]] && \
        source ~/.zconfig/tools/shell/zsh/config/${m}.zsh
done
unset _zconfig_modules m

# ── Shell options ────────────────────────────────────────
# Early: EXTENDED_GLOB must be on before the completion block below — its
# (#q...) glob qualifier parses as a literal string without it.
setopt AUTO_CD GLOB_DOTS EXTENDED_GLOB CORRECT

# ── Prompt ───────────────────────────────────────────────
command -v starship &> /dev/null && eval "$(starship init zsh)"

# ── fzf ──────────────────────────────────────────────────
if command -v fzf &> /dev/null; then
    # fzf >= 0.48 supports `--zsh`; try it directly instead of forking
    # fzf+awk+sort to compare versions. Older fzf exits non-zero — fall
    # back to the distro-packaged scripts.
    if _zconfig_fzf_init="$(fzf --zsh 2> /dev/null)"; then
        eval "$_zconfig_fzf_init"
        unset _zconfig_fzf_init
    elif [[ -f /usr/share/doc/fzf/examples/key-bindings.zsh ]]; then
        source /usr/share/doc/fzf/examples/key-bindings.zsh
        [[ -f /usr/share/doc/fzf/examples/completion.zsh ]] && \
            source /usr/share/doc/fzf/examples/completion.zsh
    fi
    # Resolve a real clipboard binary (fzf execute-silent runs in a subshell
    # without aliases, so `pbcopy` defined in linux.zsh wouldn't apply).
    if   command -v pbcopy  &> /dev/null; then _zconfig_clip="pbcopy"
    elif command -v wl-copy &> /dev/null; then _zconfig_clip="wl-copy"
    elif command -v xclip   &> /dev/null; then _zconfig_clip="xclip -selection clipboard"
    elif command -v xsel    &> /dev/null; then _zconfig_clip="xsel --clipboard --input"
    else _zconfig_clip="cat >/dev/null"   # no clipboard — drop quietly
    fi

    export FZF_DEFAULT_OPTS="--height 5 --layout=reverse --border --no-info"
    export FZF_CTRL_R_OPTS="
        --height=5
        --layout=reverse
        --border
        --no-info
        --bind 'ctrl-y:execute-silent(echo -n {2..} | ${_zconfig_clip})+abort'"
    unset _zconfig_clip
fi

# ── History ──────────────────────────────────────────────
HISTSIZE=10000
SAVEHIST=10000
HISTFILE=~/.zsh_history
setopt HIST_VERIFY SHARE_HISTORY APPEND_HISTORY INC_APPEND_HISTORY
setopt HIST_IGNORE_DUPS HIST_IGNORE_ALL_DUPS HIST_REDUCE_BLANKS HIST_IGNORE_SPACE

# ── Keybindings (emacs base + macOS-friendly word motion) ─
bindkey -e
bindkey '^A'      beginning-of-line
bindkey '^E'      end-of-line
bindkey '^[[1;3D' backward-word       # Option+Left
bindkey '^[[1;3C' forward-word        # Option+Right
bindkey '^[b'     backward-word       # Option+B
bindkey '^[f'     forward-word        # Option+F
bindkey '^[[3~'   delete-char         # Forward delete

# ── Completion ───────────────────────────────────────────
# Full compinit (with compaudit security scan) at most once a day; -C trusts
# the existing dump otherwise. (#qN.mh+24) = glob qualifier: nullglob, dump
# file modified more than 24 hours ago.
autoload -Uz compinit
if [[ -n ~/.zcompdump(#qN.mh+24) || ! -f ~/.zcompdump ]]; then
    compinit
    touch ~/.zcompdump   # compinit skips the rewrite when unchanged — bump
                         # mtime ourselves or this branch runs every shell
else
    compinit -C
fi
zstyle ':completion:*' matcher-list 'm:{a-z}={A-Za-z}'

# ── Machine-local overrides (not committed) ──────────────
# Last so it can override anything above — same pattern as
# ~/.gitconfig.local and ~/.ssh/config.local.
[[ -f ~/.zshrc.local ]] && source ~/.zshrc.local
