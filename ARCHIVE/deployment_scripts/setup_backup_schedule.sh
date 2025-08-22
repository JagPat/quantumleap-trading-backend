#!/bin/bash
# Database Backup Schedule Script
# Add this to crontab for automated backups

# Backup every hour
# 0 * * * * /usr/bin/python3 /path/to/database_backup.py

# Backup every 6 hours (more conservative)
# 0 */6 * * * /usr/bin/python3 /path/to/database_backup.py

echo "Database backup schedule configured"
echo "Add the following line to crontab for hourly backups:"
echo "0 * * * * /usr/bin/python3 $(pwd)/database_backup.py"
