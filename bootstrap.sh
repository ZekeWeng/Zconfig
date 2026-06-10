#!/bin/bash
# Remote bootstrap — run this on a fresh machine with one command:
#
#   curl -fsSL https://raw.githubusercontent.com/ZekeWeng/Zconfig/main/bootstrap.sh | bash
#
# Corp profile:
#
#   ZCONFIG_PROFILE=corp curl -fsSL https://raw.githubusercontent.com/ZekeWeng/Zconfig/main/bootstrap.sh | bash
#
# Clones the repo to ~/.zconfig (override with $ZCONFIG_DIR), installs
# Homebrew on macOS if missing (full profile only), then hands off to
# install.sh — which prompts for git identity when a terminal is attached.

set -euo pipefail
IFS=$'\n\t'

ZCONFIG_DIR="${ZCONFIG_DIR:-$HOME/.zconfig}"
ZCONFIG_REPO="${ZCONFIG_REPO:-https://github.com/ZekeWeng/Zconfig.git}"

if ! command -v git &> /dev/null; then
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "git not found. Install the Xcode Command Line Tools, then re-run:" >&2
        echo "  xcode-select --install" >&2
    else
        echo "git not found. Install it with your package manager, then re-run." >&2
    fi
    exit 1
fi

# Full profile on macOS needs Homebrew; corp profile merely uses it if present.
if [[ "$(uname)" == "Darwin" && "${ZCONFIG_PROFILE:-full}" != "corp" ]] \
    && ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    NONINTERACTIVE=1 /bin/bash -c \
        "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # brew lands outside the default PATH (Apple Silicon: /opt/homebrew).
    if [[ -x /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
fi

if [[ -d "$ZCONFIG_DIR/.git" ]]; then
    echo "Existing clone at $ZCONFIG_DIR — using it as-is."
else
    git clone "$ZCONFIG_REPO" "$ZCONFIG_DIR"
fi

exec bash "$ZCONFIG_DIR/install.sh"
