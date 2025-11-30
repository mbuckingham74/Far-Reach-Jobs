# Database Backup Scripts

Automated MySQL backup and restore scripts for Far Reach Jobs.

## Setup on Production Server

Run these as user `michael` on tachyonfuture.com:

1. **Make scripts executable:**
   ```bash
   chmod +x ~/apps/far-reach-jobs/scripts/backup-database.sh
   chmod +x ~/apps/far-reach-jobs/scripts/restore-database.sh
   ```

2. **Create backup and log directories:**
   ```bash
   mkdir -p ~/backups/far-reach-jobs
   mkdir -p ~/logs
   ```

3. **Test the backup script:**
   ```bash
   ~/apps/far-reach-jobs/scripts/backup-database.sh
   ```

4. **Set up cron job (daily at noon UTC):**
   ```bash
   crontab -e
   ```
   Add this line:
   ```
   0 12 * * * ~/apps/far-reach-jobs/scripts/backup-database.sh >> ~/logs/far-reach-jobs-backup.log 2>&1
   ```

### Timezone Note

The cron runs at a fixed UTC time (noon = 12:00 UTC). In Alaska:
- **Winter (AKST, UTC-9):** 3:00 AM
- **Summer (AKDT, UTC-8):** 4:00 AM

This is intentional - a fixed UTC time is simpler and the 1-hour shift during DST is acceptable for backups.

## Backup Script

`backup-database.sh` creates compressed MySQL dumps with automatic rotation.

### Features
- Uses `--single-transaction` for consistent InnoDB backups without locking
- Compresses backups with gzip (typically 80-90% size reduction)
- Automatically deletes backups older than retention period
- Logs all operations with timestamps

### Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKUP_DIR` | `~/backups/far-reach-jobs` | Where backups are stored |
| `RETENTION_DAYS` | `14` | Days to keep backups |
| `CONTAINER_NAME` | `far-reach-jobs-mysql` | MySQL container name |
| `DATABASE_NAME` | `far_reach_jobs` | Database to backup |

### Manual Backup
```bash
# Default settings
./backup-database.sh

# Custom retention
RETENTION_DAYS=7 ./backup-database.sh

# Custom backup location
BACKUP_DIR=/mnt/external/backups ./backup-database.sh
```

## Restore Script

`restore-database.sh` restores a compressed backup file.

### Interactive Mode (Recommended)
```bash
./restore-database.sh
```
Lists available backups and prompts for selection.

### Direct Mode
```bash
./restore-database.sh ~/backups/far-reach-jobs/far_reach_jobs_20251130_120000.sql.gz
```

### After Restore
The web container may need a restart to clear connection pools:
```bash
docker restart far-reach-jobs-web
```

## Backup File Format

Backups are named: `far_reach_jobs_YYYYMMDD_HHMMSS.sql.gz`

Example: `far_reach_jobs_20251130_120000.sql.gz`

## Monitoring

Check recent backup logs:
```bash
tail -50 ~/logs/far-reach-jobs-backup.log
```

List current backups:
```bash
ls -lh ~/backups/far-reach-jobs/
```

Check disk usage:
```bash
du -sh ~/backups/far-reach-jobs/
```

## Disaster Recovery

If the server fails completely, you'll need:

1. A backup `.sql.gz` file (copy off-server periodically!)
2. The `.env` file with credentials
3. The git repository

Recovery steps:
1. Set up new server with Docker
2. Clone repository and copy `.env`
3. Run `docker compose up -d`
4. Wait for MySQL to be healthy
5. Run `./restore-database.sh backup_file.sql.gz`

## Off-Site Backup (Local Machine)

`sync-backups-local.sh` pulls backups from the server to your local machine.

### Setup (on your Mac)

```bash
# Create local backup directory
mkdir -p ~/Backups/far-reach-jobs

# Run manually
./scripts/sync-backups-local.sh

# Or set up a daily cron job (8 AM local time)
crontab -e
# Add: 0 8 * * * /Users/michaelbuckingham/Documents/my-apps/far-reach-jobs/scripts/sync-backups-local.sh >> ~/Library/Logs/far-reach-jobs-backup-sync.log 2>&1
```

### Prerequisites
- SSH alias `tachyon` configured in `~/.ssh/config`
- SSH key authentication (no password prompts)

### Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `REMOTE_HOST` | `tachyon` | SSH host alias |
| `REMOTE_BACKUP_DIR` | `~/backups/far-reach-jobs` | Server backup path (michael's home) |
| `LOCAL_BACKUP_DIR` | `~/Backups/far-reach-jobs` | Local destination |

### How It Works
- Uses rsync to sync only new/changed files (efficient)
- `--delete` removes local files deleted from server (matches retention policy)
- Checks SSH connectivity before attempting sync
