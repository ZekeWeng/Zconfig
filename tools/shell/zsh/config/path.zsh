# Local bin
export PATH="$HOME/.local/bin:$PATH"

# Go
if command -v go &> /dev/null; then
    export GOPATH="$HOME/go"
    export PATH="$GOPATH/bin:$PATH"
fi

# Rust
if [[ -f "$HOME/.cargo/env" ]]; then
    source "$HOME/.cargo/env"
fi

# Node.js (if using nvm)
if [[ -d "$HOME/.nvm" ]]; then
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
    [ -s "$NVM_DIR/bash_completion" ] && source "$NVM_DIR/bash_completion"
fi

# Python — add every ~/Library/Python/3.x/bin that exists (macOS user-site).
# (N) is zsh nullglob: no match expands to nothing instead of erroring.
for p in "$HOME"/Library/Python/3.*/bin(N); do
    export PATH="$p:$PATH"
done

# Keg-only Homebrew formulas — link explicitly when present.
for keg in node@22 postgresql@15; do
    if [[ -d "${HOMEBREW_PREFIX:-}/opt/${keg}/bin" ]]; then
        export PATH="$HOMEBREW_PREFIX/opt/${keg}/bin:$PATH"
    fi
done
unset keg
