"""
Backup and restore utilities for audit logs.
Supports local and cloud storage (S3, Azure Blob).
"""

import sys
import json
import gzip
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from automation_orchestrator.audit import get_audit_logger


class AuditBackup:
    """Backup and restore audit logs."""
    
    def __init__(self, audit_file: str = "logs/audit.log"):
        self.audit_file = Path(audit_file)
        self.backup_dir = Path("backups/audit")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, compress: bool = True, verify: bool = True) -> dict:
        """
        Create backup of audit log.
        
        Args:
            compress: Compress backup with gzip
            verify: Verify backup integrity
        
        Returns:
            Dictionary with backup details
        """
        if not self.audit_file.exists():
            raise FileNotFoundError(f"Audit log not found: {self.audit_file}")
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"audit_backup_{timestamp}.log"
        
        if compress:
            backup_name += ".gz"
            backup_path = self.backup_dir / backup_name
            
            # Compress
            print(f"Creating compressed backup: {backup_path}")
            with open(self.audit_file, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            backup_path = self.backup_dir / backup_name
            
            # Copy
            print(f"Creating backup: {backup_path}")
            shutil.copy2(self.audit_file, backup_path)
        
        # Calculate checksum
        checksum = self._calculate_checksum(backup_path)
        
        # Get file info
        size = backup_path.stat().st_size
        size_mb = size / (1024 * 1024)
        
        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "backup_file": str(backup_path),
            "original_file": str(self.audit_file),
            "size_bytes": size,
            "size_mb": round(size_mb, 2),
            "compressed": compress,
            "checksum": checksum,
            "created_at": datetime.now().isoformat()
        }
        
        metadata_path = backup_path.with_suffix(backup_path.suffix + ".meta")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✓ Backup created: {size_mb:.2f} MB")
        print(f"✓ Checksum: {checksum}")
        
        # Verify if requested
        if verify:
            print("Verifying backup...")
            if self._verify_backup(backup_path, checksum):
                print("✓ Backup verification passed")
                metadata['verified'] = True
            else:
                print("✗ Backup verification failed")
                metadata['verified'] = False
        
        return metadata
    
    def restore_backup(self, backup_file: str, target_file: Optional[str] = None,
                      verify: bool = True) -> bool:
        """
        Restore audit log from backup.
        
        Args:
            backup_file: Path to backup file
            target_file: Target file path (default: original audit log)
            verify: Verify backup before restore
        
        Returns:
            True if successful
        """
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")
        
        # Load metadata
        metadata_path = backup_path.with_suffix(backup_path.suffix + ".meta")
        metadata = None
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        
        # Verify backup
        if verify and metadata:
            print("Verifying backup integrity...")
            if not self._verify_backup(backup_path, metadata.get('checksum')):
                raise ValueError("Backup verification failed - checksum mismatch")
            print("✓ Backup verified")
        
        # Determine target
        if target_file:
            target_path = Path(target_file)
        else:
            target_path = self.audit_file
        
        # Check if target exists
        if target_path.exists():
            response = input(f"Target file exists: {target_path}\nOverwrite? (y/n): ")
            if response.lower() != 'y':
                print("Restore cancelled")
                return False
            
            # Backup existing file
            backup_existing = target_path.with_suffix('.bak')
            print(f"Backing up existing file to: {backup_existing}")
            shutil.copy2(target_path, backup_existing)
        
        # Restore
        print(f"Restoring from: {backup_path}")
        print(f"Restoring to: {target_path}")
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        if backup_path.suffix == '.gz':
            # Decompress
            with gzip.open(backup_path, 'rb') as f_in:
                with open(target_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        else:
            # Copy
            shutil.copy2(backup_path, target_path)
        
        print(f"✓ Restore complete")
        return True
    
    def list_backups(self) -> List[dict]:
        """List all available backups."""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("audit_backup_*.log*")):
            # Skip metadata files
            if backup_file.suffix == '.meta':
                continue
            
            # Load metadata if exists
            metadata_path = backup_file.with_suffix(backup_file.suffix + ".meta")
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    backups.append(metadata)
            else:
                # Create minimal metadata
                size = backup_file.stat().st_size
                backups.append({
                    "backup_file": str(backup_file),
                    "size_bytes": size,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "compressed": backup_file.suffix == '.gz',
                    "checksum": self._calculate_checksum(backup_file)
                })
        
        return backups
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Clean up old backups, keeping only the most recent.
        
        Args:
            keep_count: Number of backups to keep
        
        Returns:
            Number of backups deleted
        """
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            print(f"Only {len(backups)} backups found, keeping all")
            return 0
        
        # Sort by timestamp (oldest first)
        backups_sorted = sorted(backups, key=lambda b: b.get('timestamp', ''))
        
        # Delete oldest
        to_delete = backups_sorted[:len(backups) - keep_count]
        deleted_count = 0
        
        for backup in to_delete:
            backup_path = Path(backup['backup_file'])
            metadata_path = backup_path.with_suffix(backup_path.suffix + ".meta")
            
            print(f"Deleting old backup: {backup_path}")
            
            if backup_path.exists():
                backup_path.unlink()
                deleted_count += 1
            
            if metadata_path.exists():
                metadata_path.unlink()
        
        print(f"✓ Deleted {deleted_count} old backups")
        return deleted_count
    
    def export_to_cloud(self, backup_file: str, provider: str, 
                       destination: str) -> bool:
        """
        Export backup to cloud storage.
        
        Args:
            backup_file: Local backup file path
            provider: Cloud provider ('s3', 'azure', 'gcs')
            destination: Cloud destination (bucket/container name)
        
        Returns:
            True if successful
        """
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")
        
        print(f"Exporting to {provider}: {destination}")
        
        if provider == 's3':
            return self._export_to_s3(backup_path, destination)
        elif provider == 'azure':
            return self._export_to_azure(backup_path, destination)
        elif provider == 'gcs':
            return self._export_to_gcs(backup_path, destination)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _export_to_s3(self, backup_path: Path, bucket: str) -> bool:
        """Export to AWS S3."""
        try:
            import boto3
            
            s3 = boto3.client('s3')
            key = f"audit-backups/{backup_path.name}"
            
            print(f"Uploading to s3://{bucket}/{key}")
            s3.upload_file(str(backup_path), bucket, key)
            print("✓ Upload complete")
            
            return True
        
        except ImportError:
            print("✗ boto3 not installed. Install with: pip install boto3")
            return False
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            return False
    
    def _export_to_azure(self, backup_path: Path, container: str) -> bool:
        """Export to Azure Blob Storage."""
        try:
            from azure.storage.blob import BlobServiceClient
            
            # Expects AZURE_STORAGE_CONNECTION_STRING env var
            import os
            conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
            if not conn_str:
                print("✗ AZURE_STORAGE_CONNECTION_STRING not set")
                return False
            
            blob_service = BlobServiceClient.from_connection_string(conn_str)
            blob_client = blob_service.get_blob_client(
                container=container,
                blob=f"audit-backups/{backup_path.name}"
            )
            
            print(f"Uploading to Azure: {container}/{backup_path.name}")
            with open(backup_path, 'rb') as f:
                blob_client.upload_blob(f, overwrite=True)
            print("✓ Upload complete")
            
            return True
        
        except ImportError:
            print("✗ azure-storage-blob not installed. Install with: pip install azure-storage-blob")
            return False
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            return False
    
    def _export_to_gcs(self, backup_path: Path, bucket: str) -> bool:
        """Export to Google Cloud Storage."""
        try:
            from google.cloud import storage
            
            client = storage.Client()
            bucket_obj = client.bucket(bucket)
            blob = bucket_obj.blob(f"audit-backups/{backup_path.name}")
            
            print(f"Uploading to GCS: {bucket}/{backup_path.name}")
            blob.upload_from_filename(str(backup_path))
            print("✓ Upload complete")
            
            return True
        
        except ImportError:
            print("✗ google-cloud-storage not installed. Install with: pip install google-cloud-storage")
            return False
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            return False
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    def _verify_backup(self, backup_path: Path, expected_checksum: str) -> bool:
        """Verify backup integrity."""
        actual_checksum = self._calculate_checksum(backup_path)
        return actual_checksum == expected_checksum


def main():
    """Run backup/restore utility."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit log backup/restore utility")
    parser.add_argument("--log-file", default="logs/audit.log",
                       help="Path to audit log file")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create backup")
    backup_parser.add_argument("--no-compress", action="store_true",
                              help="Don't compress backup")
    backup_parser.add_argument("--no-verify", action="store_true",
                              help="Skip verification")
    backup_parser.add_argument("--cloud", choices=['s3', 'azure', 'gcs'],
                              help="Upload to cloud storage")
    backup_parser.add_argument("--destination",
                              help="Cloud destination (bucket/container)")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_file", help="Backup file to restore")
    restore_parser.add_argument("--target", help="Target file (default: original)")
    restore_parser.add_argument("--no-verify", action="store_true",
                               help="Skip verification")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List backups")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old backups")
    cleanup_parser.add_argument("--keep", type=int, default=10,
                               help="Number of backups to keep")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Create backup manager
    backup_mgr = AuditBackup(args.log_file)
    
    try:
        if args.command == "backup":
            metadata = backup_mgr.create_backup(
                compress=not args.no_compress,
                verify=not args.no_verify
            )
            
            # Upload to cloud if requested
            if args.cloud and args.destination:
                backup_mgr.export_to_cloud(
                    metadata['backup_file'],
                    args.cloud,
                    args.destination
                )
        
        elif args.command == "restore":
            backup_mgr.restore_backup(
                args.backup_file,
                target_file=args.target,
                verify=not args.no_verify
            )
        
        elif args.command == "list":
            backups = backup_mgr.list_backups()
            
            if not backups:
                print("No backups found")
            else:
                print(f"\nFound {len(backups)} backup(s):\n")
                print("-" * 80)
                
                for i, backup in enumerate(backups, 1):
                    print(f"{i}. {Path(backup['backup_file']).name}")
                    print(f"   Size: {backup['size_mb']} MB")
                    print(f"   Compressed: {backup.get('compressed', False)}")
                    if 'timestamp' in backup:
                        print(f"   Created: {backup['timestamp']}")
                    if 'checksum' in backup:
                        print(f"   Checksum: {backup['checksum'][:16]}...")
                    print()
        
        elif args.command == "cleanup":
            backup_mgr.cleanup_old_backups(keep_count=args.keep)
    
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
