#!/bin/bash
#
# Far Reach Jobs - Database Restore Script
#
# Restores a MySQL backup from a compressed .sql.gz file.
# USE WITH CAUTION: This will overwrite all existing data!
#
# Usage:
#   ./restore-database.sh /path/to/backup.sql.gz
#   ./restore-database.sh  # Lists available backups and prompts
#

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/far-reach-jobs}"
CONTAINER_NAME="${CONTAINER_NAME:-far-reach-jobs-mysql}"
DATABASE_NAME="${DATABASE_NAME:-far_reach_jobs}"

# Colors for output
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    CYAN=''
    NC=''
fi

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    log_error "Container '$CONTAINER_NAME' is not running"
    exit 1
fi

# If no backup file specified, list available backups
if [ $# -eq 0 ]; then
    echo -e "\n${CYAN}Available backups in $BACKUP_DIR:${NC}\n"

    if [ -d "$BACKUP_DIR" ]; then
        BACKUPS=$(find "$BACKUP_DIR" -name "${DATABASE_NAME}_*.sql.gz" -type f | sort -r)

        if [ -z "$BACKUPS" ]; then
            log_error "No backups found in $BACKUP_DIR"
            exit 1
        fi

        i=1
        declare -a BACKUP_ARRAY
        while IFS= read -r backup; do
            SIZE=$(du -h "$backup" | cut -f1)
            DATE=$(basename "$backup" | sed "s/${DATABASE_NAME}_//" | sed 's/.sql.gz//')
            FORMATTED_DATE=$(echo "$DATE" | sed 's/_/ /' | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3/')
            echo -e "  ${CYAN}$i)${NC} $(basename "$backup") - ${SIZE} - ${FORMATTED_DATE}"
            BACKUP_ARRAY[$i]="$backup"
            ((i++))
        done <<< "$BACKUPS"

        echo ""
        read -p "Enter backup number to restore (or 'q' to quit): " SELECTION

        if [ "$SELECTION" = "q" ] || [ "$SELECTION" = "Q" ]; then
            echo "Aborted."
            exit 0
        fi

        if ! [[ "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -lt 1 ] || [ "$SELECTION" -ge "$i" ]; then
            log_error "Invalid selection"
            exit 1
        fi

        BACKUP_FILE="${BACKUP_ARRAY[$SELECTION]}"
    else
        log_error "Backup directory $BACKUP_DIR does not exist"
        exit 1
    fi
else
    BACKUP_FILE="$1"
fi

# Validate backup file
if [ ! -f "$BACKUP_FILE" ]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

if [[ ! "$BACKUP_FILE" =~ \.sql\.gz$ ]]; then
    log_error "Backup file must be a .sql.gz file"
    exit 1
fi

# Confirmation prompt
echo ""
log_warn "This will OVERWRITE ALL DATA in database '$DATABASE_NAME'!"
log_warn "Backup file: $(basename "$BACKUP_FILE")"
echo ""
read -p "Are you sure you want to restore? Type 'yes' to confirm: " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Get MySQL root password
MYSQL_ROOT_PASSWORD=$(docker exec "$CONTAINER_NAME" printenv MYSQL_ROOT_PASSWORD 2>/dev/null) || {
    log_error "Could not retrieve MYSQL_ROOT_PASSWORD from container"
    exit 1
}

# Perform restore
log_info "Restoring from $(basename "$BACKUP_FILE")..."
log_info "This may take a few minutes depending on backup size..."

# Capture stderr to show actual error on failure
STDERR_FILE=$(mktemp)
trap "rm -f '$STDERR_FILE'" EXIT

if gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" mysql \
    -u root \
    -p"$MYSQL_ROOT_PASSWORD" \
    "$DATABASE_NAME" 2>"$STDERR_FILE"; then

    echo ""
    log_info "Restore completed successfully!"
    log_info "Verify your data and restart the web container if needed:"
    echo -e "  ${CYAN}docker restart far-reach-jobs-web${NC}"
else
    log_error "Restore failed"
    if [ -s "$STDERR_FILE" ]; then
        log_error "MySQL error: $(cat "$STDERR_FILE")"
    fi
    exit 1
fi
