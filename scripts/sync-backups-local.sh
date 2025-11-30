#!/bin/bash
#
# Far Reach Jobs - Sync Backups to Local Machine
#
# Downloads database backups from the production server to your local machine.
# Run this periodically (manually or via cron) for off-site backup protection.
#
# Usage:
#   ./sync-backups-local.sh
#
# Prerequisites:
#   - SSH access to tachyon (tachyonfuture.com)
#   - SSH key authentication configured
#
# Local cron example (daily at 8 AM):
#   0 8 * * * /Users/michaelbuckingham/Documents/my-apps/far-reach-jobs/scripts/sync-backups-local.sh >> ~/Library/Logs/far-reach-jobs-backup-sync.log 2>&1
#

set -euo pipefail

# Configuration
REMOTE_HOST="${REMOTE_HOST:-tachyon}"
REMOTE_BACKUP_DIR="${REMOTE_BACKUP_DIR:-backups/far-reach-jobs}"  # Relative to remote user's home
LOCAL_BACKUP_DIR="${LOCAL_BACKUP_DIR:-$HOME/Backups/far-reach-jobs}"

# Colors for output
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}

# Create local backup directory if it doesn't exist
mkdir -p "$LOCAL_BACKUP_DIR"

log_info "Syncing backups from $REMOTE_HOST:$REMOTE_BACKUP_DIR"
log_info "Local directory: $LOCAL_BACKUP_DIR"

# Check SSH connectivity
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$REMOTE_HOST" "echo ok" &>/dev/null; then
    log_error "Cannot connect to $REMOTE_HOST - check SSH config and network"
    exit 1
fi

# Check if remote backup directory exists
if ! ssh "$REMOTE_HOST" "test -d ~/$REMOTE_BACKUP_DIR"; then
    log_warn "Remote backup directory does not exist yet: $REMOTE_BACKUP_DIR"
    log_warn "Run a backup on the server first"
    exit 0
fi

# Sync backups using rsync
# -a: archive mode (preserves permissions, timestamps, etc.)
# -v: verbose
# -z: compress during transfer
# --delete: remove local files that no longer exist on server (respects retention)
if rsync -avz --delete \
    "$REMOTE_HOST:~/$REMOTE_BACKUP_DIR/" \
    "$LOCAL_BACKUP_DIR/"; then

    # Count local backups
    BACKUP_COUNT=$(find "$LOCAL_BACKUP_DIR" -name "*.sql.gz" | wc -l | tr -d ' ')
    TOTAL_SIZE=$(du -sh "$LOCAL_BACKUP_DIR" 2>/dev/null | cut -f1)

    log_info "Sync complete. Local backups: $BACKUP_COUNT, Total size: $TOTAL_SIZE"

    # Show most recent backup
    LATEST=$(ls -t "$LOCAL_BACKUP_DIR"/*.sql.gz 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        log_info "Latest backup: $(basename "$LATEST")"
    fi
else
    log_error "rsync failed"
    exit 1
fi
