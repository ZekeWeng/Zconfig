#!/bin/bash
# Nerd Fonts — pinned releases with SHA256 verification (Linux only; macOS uses brew casks).
# Bump NERD_FONTS_VERSION + hashes when upgrading.

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

NERD_FONTS_VERSION="v3.4.0"

# Each entry: <font-name>:<sha256>. Add a line to install another font.
NERD_FONTS_LIST="
JetBrainsMono:76f05ff3ace48a464a6ca57977998784ff7bdbb65a6d915d7e401cd3927c493c
FiraCode:7cc4ffd8f7a1fc914cdab7b149808298165ff7a7f40e40d82dea9ebe41e8ca0b
"

_install_one_nerd_font() {
    local font="$1" sha="$2" font_dir="$3"
    local zip="/tmp/${font}.zip"
    # shellcheck disable=SC2064  # bake the path now; RETURN traps fire in each enclosing frame
    trap "rm -f '$zip'" RETURN
    verify_and_download \
        "https://github.com/ryanoasis/nerd-fonts/releases/download/${NERD_FONTS_VERSION}/${font}.zip" \
        "$zip" \
        "$sha"
    unzip -o "$zip" -d "$font_dir" > /dev/null
    log_ok "  ${font} installed"
}

install_nerd_fonts() {
    log_info "Installing Nerd Fonts (${NERD_FONTS_VERSION})..."
    local font_dir="$HOME/.local/share/fonts"
    mkdir -p "$font_dir"

    local font sha
    while IFS=: read -r font sha; do
        [[ -z "$font" ]] && continue
        if compgen -G "${font_dir}/${font}*" > /dev/null; then
            log_info "  ${font} already present; skipping"
            continue
        fi
        _install_one_nerd_font "$font" "$sha" "$font_dir"
    done <<< "$NERD_FONTS_LIST"
    fc-cache -f > /dev/null
}
