#!/bin/bash
# Visual Studio Code — cross-platform.
#  macOS: direct download from Microsoft, verified against their update API hash.
#  Linux: Microsoft's signed apt/dnf repo, or Code OSS on Arch.
#
# Drift policy: we do NOT pin a specific VSCode version at the script level —
# `make install` installs whatever's current at run time. To prevent the
# bundle from drifting *between launches*, we disable VSCode's auto-updater
# (settings.json: update.mode=manual). Bumping the version = re-run
# `make install` (or click Check for Updates inside VSCode).

source "${ZCONFIG_DIR:-$HOME/.zconfig}/lib/bootstrap.sh"

install_vscode() {
    if command -v code &> /dev/null; then
        log_info "VSCode already installed at $(command -v code); skipping install"
    else
        case "$OS_KIND" in
            darwin) _install_vscode_macos ;;
            linux)  _install_vscode_linux ;;
            *)      log_err "vscode: unsupported OS"; return 1 ;;
        esac
    fi
    _disable_vscode_autoupdate
}

# Lock VSCode against silent in-place upgrades. Runs on every install — safe
# because the writer is idempotent.
_disable_vscode_autoupdate() {
    local settings_dir
    case "$OS_KIND" in
        darwin) settings_dir="$HOME/Library/Application Support/Code/User" ;;
        linux)  settings_dir="$HOME/.config/Code/User" ;;
        *)      return 0 ;;
    esac
    local settings="$settings_dir/settings.json"
    if [[ -f "$settings" ]]; then
        if grep -q '"update.mode"' "$settings"; then
            return 0
        fi
        log_info "VSCode settings.json exists — to lock the bundle add:"
        log_info '  "update.mode": "manual",'
        log_info '  "extensions.autoUpdate": false'
        return 0
    fi
    mkdir -p "$settings_dir"
    cat > "$settings" <<'JSON'
{
    "update.mode": "manual",
    "extensions.autoUpdate": false
}
JSON
    log_ok "Wrote $settings — VSCode auto-update disabled"
}

# macOS — direct download with two-call hash verification.
# The update API and the binary live on the same domain, so this protects
# against transit tampering, not against a domain compromise.
_install_vscode_macos() {
    log_info "Querying VSCode update API..."
    local metadata
    metadata="$(curl -fsSL "https://update.code.visualstudio.com/api/update/darwin-universal/stable/latest")"
    local url expected_hash version
    url="$(echo "$metadata"           | python3 -c 'import json,sys;print(json.load(sys.stdin)["url"])')"
    expected_hash="$(echo "$metadata" | python3 -c 'import json,sys;print(json.load(sys.stdin)["sha256hash"])')"
    version="$(echo "$metadata"       | python3 -c 'import json,sys;print(json.load(sys.stdin)["productVersion"])')"

    log_info "Downloading VSCode ${version}..."
    local zip_path
    zip_path="$(mktemp -t vscode.XXXXXX).zip"
    # shellcheck disable=SC2064  # bake the path now; RETURN traps fire in each enclosing frame
    trap "rm -f '$zip_path'" RETURN
    verify_and_download "$url" "$zip_path" "$expected_hash"

    log_info "Installing to /Applications..."
    [[ -d "/Applications/Visual Studio Code.app" ]] && rm -rf "/Applications/Visual Studio Code.app"
    unzip -q "$zip_path" -d /Applications

    local brew_prefix
    brew_prefix="$(brew --prefix)"
    ln -sf "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" "${brew_prefix}/bin/code"
    log_ok "VSCode ${version} installed."
}

# Linux — Microsoft signed repo on apt/dnf, Code OSS on Arch.
_install_vscode_linux() {
    log_info "Installing Visual Studio Code..."
    case "$PKG_MANAGER" in
        apt)
            sudo install -d -m 0755 /etc/apt/keyrings
            curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
                | sudo gpg --dearmor -o /etc/apt/keyrings/packages.microsoft.gpg
            echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" \
                | sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null
            sudo apt-get update
            pkg_install code
            ;;
        dnf)
            sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
            sudo tee /etc/yum.repos.d/vscode.repo > /dev/null <<'REPO'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
REPO
            pkg_install code
            ;;
        pacman)
            # Arch's extra repo ships Code OSS (FOSS build). For the proprietary
            # Microsoft build, install `visual-studio-code-bin` via an AUR helper.
            pkg_install code
            ;;
        *)
            log_err "vscode: unsupported package manager"
            return 1
            ;;
    esac
}
