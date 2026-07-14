#!/bin/bash
# Sync workspace to GDrive using rclone
# Usage: ./sync_gdrive.sh

# 1. First, make sure rclone is configured.
# Run: docker exec -it tg-admin-bot rclone config
# and configure a remote named 'gdrive'.

echo "Starting sync of /workspace to gdrive:llm_backup..."
rclone sync /workspace gdrive:llm_backup -v
echo "Sync completed."
