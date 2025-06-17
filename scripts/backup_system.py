#!/usr/bin/env python3
# Automatic Backup Script - scripts/backup_system.py

import sqlite3
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = PROJECT_ROOT / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def backup_databases():
    """Backup all databases"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Backup user database
    user_db = PROJECT_ROOT / "production_users.db"
    if user_db.exists():
        backup_path = BACKUP_DIR / f"users_backup_{timestamp}.db"
        shutil.copy2(user_db, backup_path)
        logger.info(f"✅ User database backed up: {backup_path}")

    # Backup face encodings cache
    cache_file = PROJECT_ROOT / "face_encodings_cache.pkl"
    if cache_file.exists():
        backup_cache = BACKUP_DIR / f"face_cache_backup_{timestamp}.pkl"
        shutil.copy2(cache_file, backup_cache)
        logger.info(f"✅ Face cache backed up: {backup_cache}")

def backup_photos():
    """Backup student photos"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photos_dir = PROJECT_ROOT / "static" / "known_faces"

    if photos_dir.exists():
        backup_zip = BACKUP_DIR / f"photos_backup_{timestamp}.zip"

        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in photos_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(photos_dir)
                    zipf.write(file_path, arcname)

        logger.info(f"✅ Photos backed up: {backup_zip}")

def cleanup_old_backups(days_to_keep=30):
    """Remove backups older than specified days"""
    cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)

    for backup_file in BACKUP_DIR.glob("*"):
        if backup_file.stat().st_mtime < cutoff_time:
            backup_file.unlink()
            logger.info(f"🗑️ Removed old backup: {backup_file}")

if __name__ == "__main__":
    logger.info("🔄 Starting system backup...")
    backup_databases()
    backup_photos()
    cleanup_old_backups()
    logger.info("✅ Backup completed!")
