# Sourced by zsh on every shell startup.
# Keep this small — heavy work belongs in .zshrc.

# Load .env (key=value pairs, never executed). Parser lives in lib/env.sh
# so install.sh and the shell share a single implementation.
if [[ -f "$HOME/.zconfig/lib/env.sh" ]]; then
    source "$HOME/.zconfig/lib/env.sh"
    load_env "$HOME/.zconfig/.env"
fi

# XDG Base Directories
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CACHE_HOME="$HOME/.cache"

# Editor
export EDITOR="nvim"
export VISUAL="nvim"

# Locale
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"

# Homebrew (macOS — Apple Silicon vs. Intel)
if [[ -d "/opt/homebrew" ]]; then
    export HOMEBREW_PREFIX="/opt/homebrew"
elif [[ -d "/usr/local/Homebrew" ]]; then
    export HOMEBREW_PREFIX="/usr/local"
fi
if [[ -n "${HOMEBREW_PREFIX:-}" ]]; then
    export HOMEBREW_CELLAR="$HOMEBREW_PREFIX/Cellar"
    export HOMEBREW_REPOSITORY="$HOMEBREW_PREFIX"
    export PATH="$HOMEBREW_PREFIX/bin:$HOMEBREW_PREFIX/sbin:$PATH"
    export MANPATH="$HOMEBREW_PREFIX/share/man:$MANPATH"
    export INFOPATH="$HOMEBREW_PREFIX/share/info:$INFOPATH"
fi
