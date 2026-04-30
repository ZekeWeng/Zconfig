#!/bin/bash
# Snapshots the home-directory dotfiles listed in ZCONFIG_SYMLINKS to
# $HOME/.zconfig_backup, emits a restore.sh, and trims to the most
# recent five backups.

set -euo pipefail
IFS=$'\n\t'

ZCONFIG_DIR="${ZCONFIG_DIR:-$HOME/.zconfig}"
source "$ZCONFIG_DIR/lib/common.sh"
source "$ZCONFIG_DIR/bootstrap/symlinks.sh"

BACKUP_DIR="$HOME/.zconfig_backup"
BACKUP_PATH="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S)"

log_ok "Creating backup..."
mkdir -p "$BACKUP_PATH"

# Copy each symlink target (file or directory) into the backup.
for entry in "${ZCONFIG_SYMLINKS[@]}"; do
    tgt="${entry##*::}"
    src_path="$HOME/$tgt"
    [[ -e "$src_path" ]] || continue
    mkdir -p "$BACKUP_PATH/$(dirname "$tgt")"
    cp -R "$src_path" "$BACKUP_PATH/$tgt"
    log_info "  saved $tgt"
done

# Emit a restore script that walks the same paths.
{
    cat <<'SH'
#!/bin/bash
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
SH
    printf 'TARGETS=(\n'
    for entry in "${ZCONFIG_SYMLINKS[@]}"; do
        printf '    %q\n' "${entry##*::}"
    done
    printf ')\n'
    cat <<'SH'
for tgt in "${TARGETS[@]}"; do
    [[ -e "$DIR/$tgt" ]] || continue
    mkdir -p "$HOME/$(dirname "$tgt")"
    cp -R "$DIR/$tgt" "$HOME/$tgt"
    echo "restored $tgt"
done
SH
} > "$BACKUP_PATH/restore.sh"
chmod +x "$BACKUP_PATH/restore.sh"

log_ok "Backup written to $BACKUP_PATH"
log_info "To restore: $BACKUP_PATH/restore.sh"

# Keep only the 5 most recent backups (lexical sort = chronological).
shopt -s nullglob
backups=("$BACKUP_DIR"/backup_*)
if (( ${#backups[@]} > 5 )); then
    for (( i=0; i<${#backups[@]}-5; i++ )); do
        rm -rf -- "${backups[i]}"
    done
fi
shopt -u nullglob
