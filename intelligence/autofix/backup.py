"""
Backup and rollback system for autofix operations.

This module provides comprehensive backup management with versioning,
automatic cleanup, and rollback capabilities for safe autofix operations.
"""

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from .models import AutofixConfig

logger = logging.getLogger(__name__)


@dataclass
class BackupMetadata:
    """Metadata for a backup operation."""

    backup_id: str
    timestamp: datetime
    files: list[str]
    operation_type: str
    size_bytes: int
    description: str = ""


class BackupManager:
    """Manages file backups and rollback operations."""

    def __init__(self, config: AutofixConfig):
        self.config = config
        self.backup_dir = Path.cwd() / ".solve" / "backups"
        self.metadata_file = self.backup_dir / "metadata.json"
        self.max_backups = 50
        self.cleanup_days = 30

        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(
        self, files: list[Path], operation_type: str = "autofix"
    ) -> str:
        """Create a backup of specified files."""
        if not self.config.create_backups:
            return "backup_disabled"

        backup_id = str(uuid4())
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        try:
            total_size = 0
            backed_up_files = []

            for file_path in files:
                if not file_path.exists():
                    logger.warning(f"File not found for backup: {file_path}")
                    continue

                # Calculate relative path to maintain directory structure
                try:
                    rel_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    # File is outside current directory, use absolute path
                    rel_path = Path(file_path.name)

                backup_file_path = backup_path / rel_path
                backup_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy file
                shutil.copy2(file_path, backup_file_path)
                total_size += file_path.stat().st_size
                backed_up_files.append(str(file_path))

            # Create metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                timestamp=datetime.now(),
                files=backed_up_files,
                operation_type=operation_type,
                size_bytes=total_size,
                description=f"Backup for {operation_type} operation",
            )

            # Save metadata
            await self._save_metadata(metadata)

            logger.info(
                f"Created backup {backup_id} with {len(backed_up_files)} files "
                f"({total_size} bytes)",
            )
            return backup_id

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            # Cleanup failed backup
            if backup_path.exists():
                shutil.rmtree(backup_path, ignore_errors=True)
            raise

    async def rollback(self, backup_id: str) -> bool:
        """Rollback files from a backup."""
        if backup_id == "backup_disabled":
            logger.warning("Cannot rollback: backups were disabled")
            return False

        backup_path = self.backup_dir / backup_id
        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_id}")
            return False

        try:
            # Load metadata
            metadata = await self._load_metadata(backup_id)
            if not metadata:
                logger.error(f"No metadata found for backup: {backup_id}")
                return False

            # Restore files
            restored_count = 0
            for file_path_str in metadata.files:
                file_path = Path(file_path_str)

                try:
                    rel_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    rel_path = Path(file_path.name)

                backup_file_path = backup_path / rel_path

                if backup_file_path.exists():
                    # Ensure parent directory exists
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    # Restore file
                    shutil.copy2(backup_file_path, file_path)
                    restored_count += 1
                else:
                    logger.warning(f"Backup file not found: {backup_file_path}")

            logger.info(f"Restored {restored_count} files from backup {backup_id}")
            return restored_count > 0

        except Exception as e:
            logger.error(f"Failed to rollback backup {backup_id}: {e}")
            return False

    async def list_backups(self) -> list[BackupMetadata]:
        """List all available backups."""
        try:
            all_metadata = await self._load_all_metadata()
            return sorted(all_metadata, key=lambda m: m.timestamp, reverse=True)
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []

    async def cleanup_old_backups(self) -> int:
        """Clean up old backups based on retention policy."""
        try:
            all_metadata = await self._load_all_metadata()

            # Sort by timestamp (oldest first)
            sorted_metadata = sorted(all_metadata, key=lambda m: m.timestamp)

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.cleanup_days)

            # Identify backups to remove
            to_remove = []

            # Remove by age
            for metadata in sorted_metadata:
                if metadata.timestamp < cutoff_date:
                    to_remove.append(metadata)

            # Remove by count (keep only max_backups)
            if len(sorted_metadata) > self.max_backups:
                excess_count = len(sorted_metadata) - self.max_backups
                to_remove.extend(sorted_metadata[:excess_count])

            # Remove duplicates
            to_remove = list(set(to_remove))

            # Delete backup directories
            removed_count = 0
            for metadata in to_remove:
                backup_path = self.backup_dir / metadata.backup_id
                if backup_path.exists():
                    shutil.rmtree(backup_path, ignore_errors=True)
                    removed_count += 1

            # Update metadata file
            remaining_metadata = [m for m in all_metadata if m not in to_remove]
            await self._save_all_metadata(remaining_metadata)

            logger.info(f"Cleaned up {removed_count} old backups")
            return removed_count

        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0

    async def get_backup_info(self, backup_id: str) -> BackupMetadata | None:
        """Get information about a specific backup."""
        return await self._load_metadata(backup_id)

    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a specific backup."""
        try:
            backup_path = self.backup_dir / backup_id
            if backup_path.exists():
                shutil.rmtree(backup_path)

            # Remove from metadata
            all_metadata = await self._load_all_metadata()
            remaining_metadata = [m for m in all_metadata if m.backup_id != backup_id]
            await self._save_all_metadata(remaining_metadata)

            logger.info(f"Deleted backup {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False

    async def _save_metadata(self, metadata: BackupMetadata) -> None:
        """Save metadata for a backup."""
        try:
            all_metadata = await self._load_all_metadata()
            all_metadata.append(metadata)
            await self._save_all_metadata(all_metadata)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            raise

    async def _load_metadata(self, backup_id: str) -> BackupMetadata | None:
        """Load metadata for a specific backup."""
        try:
            all_metadata = await self._load_all_metadata()
            for metadata in all_metadata:
                if metadata.backup_id == backup_id:
                    return metadata
            return None
        except Exception as e:
            logger.error(f"Failed to load metadata for {backup_id}: {e}")
            return None

    async def _load_all_metadata(self) -> list[BackupMetadata]:
        """Load all backup metadata."""
        try:
            if not self.metadata_file.exists():
                return []

            with open(self.metadata_file) as f:
                data = json.load(f)

            metadata_list = []
            for item in data:
                # Convert timestamp string back to datetime
                item["timestamp"] = datetime.fromisoformat(item["timestamp"])
                metadata_list.append(BackupMetadata(**item))

            return metadata_list

        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return []

    async def _save_all_metadata(self, metadata_list: list[BackupMetadata]) -> None:
        """Save all backup metadata."""
        try:
            data = []
            for metadata in metadata_list:
                item = asdict(metadata)
                # Convert datetime to string for JSON serialization
                item["timestamp"] = metadata.timestamp.isoformat()
                data.append(item)

            with open(self.metadata_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            raise

    def get_backup_size(self) -> int:
        """Get total size of all backups in bytes."""
        try:
            total_size = 0
            for item in self.backup_dir.iterdir():
                if item.is_dir():
                    total_size += sum(
                        f.stat().st_size for f in item.rglob("*") if f.is_file()
                    )
            return total_size
        except Exception as e:
            logger.error(f"Failed to calculate backup size: {e}")
            return 0
