#!/bin/bash
#
# Far Reach Jobs - Database Backup Script
#
# Creates compressed MySQL backups with automatic rotation.
# Designed to run via cron on the production server.
#
# Usage:
#   ./backup-database.sh                    # Uses defaults
#   BACKUP_DIR=/custom/path ./backup-database.sh
#   RETENTION_DAYS=7 ./backup-database.sh   # Keep only 7 days
#
# Cron example (daily at noon UTC - see README for timezone notes):
#   0 12 * * * ~/apps/far-reach-jobs/scripts/backup-database.sh >> ~/logs/far-reach-jobs-backup.log 2>&1
#

set -euo pipefail

# Configuration (can be overridden via environment variables)
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/far-reach-jobs}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
CONTAINER_NAME="${CONTAINER_NAME:-far-reach-jobs-mysql}"
DATABASE_NAME="${DATABASE_NAME:-far_reach_jobs}"

# Timestamp for backup filename
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DATABASE_NAME}_${DATE}.sql"

# Colors for output (disabled if not a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
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

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_error "Container '$CONTAINER_NAME' is not running"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

log_info "Starting backup of database '$DATABASE_NAME'"
log_info "Backup directory: $BACKUP_DIR"

# Get MySQL root password from container environment
MYSQL_ROOT_PASSWORD=$(docker exec "$CONTAINER_NAME" printenv MYSQL_ROOT_PASSWORD 2>/dev/null) || {
    log_error "Could not retrieve MYSQL_ROOT_PASSWORD from container"
    exit 1
}

# Create backup using mysqldump
# --single-transaction: Consistent backup without locking tables (InnoDB)
# --routines: Include stored procedures and functions
# --triggers: Include triggers
# --quick: Retrieve rows one at a time (memory efficient for large tables)
log_info "Running mysqldump..."

# Capture stderr to a temp file so we can log it on failure
STDERR_FILE=$(mktemp)
trap "rm -f '$STDERR_FILE'" EXIT

if docker exec "$CONTAINER_NAME" mysqldump \
    -u root \
    -p"$MYSQL_ROOT_PASSWORD" \
    --single-transaction \
    --routines \
    --triggers \
    --quick \
    "$DATABASE_NAME" > "$BACKUP_FILE" 2>"$STDERR_FILE"; then

    # Check if backup file has content
    if [ ! -s "$BACKUP_FILE" ]; then
        log_error "Backup file is empty"
        rm -f "$BACKUP_FILE"
        exit 1
    fi

    log_info "Compressing backup..."
    gzip "$BACKUP_FILE"

    COMPRESSED_FILE="${BACKUP_FILE}.gz"
    BACKUP_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)

    log_info "Backup completed: $(basename "$COMPRESSED_FILE") ($BACKUP_SIZE)"
else
    log_error "mysqldump failed"
    # Log the actual error for troubleshooting
    if [ -s "$STDERR_FILE" ]; then
        log_error "MySQL error: $(cat "$STDERR_FILE")"
    fi
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Clean up old backups
log_info "Cleaning up backups older than $RETENTION_DAYS days..."
DELETED_COUNT=$(find "$BACKUP_DIR" -name "${DATABASE_NAME}_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)

if [ "$DELETED_COUNT" -gt 0 ]; then
    log_info "Deleted $DELETED_COUNT old backup(s)"
fi

# Show current backup status
TOTAL_BACKUPS=$(find "$BACKUP_DIR" -name "${DATABASE_NAME}_*.sql.gz" | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)

log_info "Backup complete. Total backups: $TOTAL_BACKUPS, Total size: $TOTAL_SIZE"
