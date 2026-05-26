#!/bin/bash
# Backup the SQLite database
# Usage: bash scripts/backup_db.sh

set -e

DB_DIR="data"
BACKUP_DIR="data/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_DIR/gift_cards.db" ]; then
    cp "$DB_DIR/gift_cards.db" "$BACKUP_DIR/gift_cards_$TIMESTAMP.db"
    echo "✅ Database backed up to: $BACKUP_DIR/gift_cards_$TIMESTAMP.db"
    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/*.db | tail -n +11 | xargs -r rm
else
    echo "⚠️ No database found at $DB_DIR/gift_cards.db"
fi