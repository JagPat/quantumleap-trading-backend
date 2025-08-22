#!/usr/bin/env python3
"""
Database Backup Script for Production Trading Engine
"""

import os
import shutil
import sqlite3
import gzip
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

class DatabaseBackupManager:
    def __init__(self):
        self.db_path = "production_trading.db"
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        self.retention_days = 30
        self.max_backups = 100
    
    def create_backup(self):
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"trading_db_backup_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # Create backup copy
            shutil.copy2(self.db_path, backup_path)
            
            # Compress backup
            compressed_path = backup_path.with_suffix('.db.gz')
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed backup
            backup_path.unlink()
            
            # Create backup metadata
            metadata = {
                "backup_time": datetime.now().isoformat(),
                "original_size": os.path.getsize(self.db_path),
                "compressed_size": os.path.getsize(compressed_path),
                "backup_file": str(compressed_path)
            }
            
            metadata_path = compressed_path.with_suffix('.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"✅ Backup created: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        backup_files = list(self.backup_dir.glob("trading_db_backup_*.db.gz"))
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Keep only the most recent backups within retention period
        kept_backups = []
        removed_count = 0
        
        for backup_file in backup_files:
            backup_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if len(kept_backups) < self.max_backups and backup_time > cutoff_date:
                kept_backups.append(backup_file)
            else:
                # Remove old backup and its metadata
                backup_file.unlink()
                metadata_file = backup_file.with_suffix('.json')
                if metadata_file.exists():
                    metadata_file.unlink()
                removed_count += 1
        
        if removed_count > 0:
            print(f"🗑️ Removed {removed_count} old backups")
    
    def verify_backup(self, backup_path):
        """Verify backup integrity"""
        try:
            # Decompress and test database
            with tempfile.NamedTemporaryFile(suffix='.db') as temp_db:
                with gzip.open(backup_path, 'rb') as f_in:
                    temp_db.write(f_in.read())
                    temp_db.flush()
                
                # Test database connection and basic query
                conn = sqlite3.connect(temp_db.name)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                conn.close()
                
                if len(tables) > 0:
                    print(f"✅ Backup verified: {len(tables)} tables found")
                    return True
                else:
                    print(f"❌ Backup verification failed: No tables found")
                    return False
                    
        except Exception as e:
            print(f"❌ Backup verification failed: {e}")
            return False
    
    def run_backup_cycle(self):
        """Run complete backup cycle"""
        print(f"🔄 Starting backup cycle at {datetime.now()}")
        
        # Create backup
        backup_path = self.create_backup()
        
        if backup_path:
            # Verify backup
            if self.verify_backup(backup_path):
                print("✅ Backup cycle completed successfully")
            else:
                print("⚠️ Backup created but verification failed")
        
        # Cleanup old backups
        self.cleanup_old_backups()

if __name__ == "__main__":
    backup_manager = DatabaseBackupManager()
    backup_manager.run_backup_cycle()
