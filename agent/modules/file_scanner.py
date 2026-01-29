"""
File Scanner Module for Endpoint Security Agent

Provides:
- Real-time file monitoring using watchdog
- Incremental backup to S3
- File hash tracking for deduplication
- Smart path exclusions
"""

import os
import sqlite3
import threading
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
    FileMovedEvent,
    DirCreatedEvent,
    DirModifiedEvent,
    DirDeletedEvent,
    DirMovedEvent
)

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.s3_client import S3Client, calculate_file_hash


@dataclass
class FileInfo:
    """Information about a file for backup tracking."""
    path: str
    size: int
    modified_time: float
    hash: str
    backed_up: bool = False
    backup_time: Optional[float] = None
    s3_key: Optional[str] = None


class HashDatabase:
    """
    SQLite database for tracking file hashes and backup state.
    
    Enables incremental backups by storing file hashes.
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db()
    
    def _ensure_db(self):
        """Create database and tables if they don't exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    size INTEGER,
                    modified_time REAL,
                    hash TEXT,
                    backed_up INTEGER DEFAULT 0,
                    backup_time REAL,
                    s3_key TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_hash ON files(hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_backed_up ON files(backed_up)
            """)
            conn.commit()
    
    def get_file(self, path: str) -> Optional[FileInfo]:
        """Get file info from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT path, size, modified_time, hash, backed_up, backup_time, s3_key "
                "FROM files WHERE path = ?",
                (path,)
            )
            row = cursor.fetchone()
            if row:
                return FileInfo(
                    path=row[0],
                    size=row[1],
                    modified_time=row[2],
                    hash=row[3],
                    backed_up=bool(row[4]),
                    backup_time=row[5],
                    s3_key=row[6]
                )
        return None
    
    def upsert_file(self, file_info: FileInfo):
        """Insert or update file info."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO files 
                (path, size, modified_time, hash, backed_up, backup_time, s3_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                file_info.path,
                file_info.size,
                file_info.modified_time,
                file_info.hash,
                int(file_info.backed_up),
                file_info.backup_time,
                file_info.s3_key
            ))
            conn.commit()
    
    def mark_backed_up(self, path: str, s3_key: str):
        """Mark a file as backed up."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE files SET backed_up = 1, backup_time = ?, s3_key = ?
                WHERE path = ?
            """, (datetime.now().timestamp(), s3_key, path))
            conn.commit()
    
    def remove_file(self, path: str):
        """Remove file from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM files WHERE path = ?", (path,))
            conn.commit()
    
    def get_pending_backups(self, limit: int = 1000) -> List[FileInfo]:
        """Get files that need to be backed up."""
        files = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT path, size, modified_time, hash, backed_up, backup_time, s3_key "
                "FROM files WHERE backed_up = 0 LIMIT ?",
                (limit,)
            )
            for row in cursor:
                files.append(FileInfo(
                    path=row[0],
                    size=row[1],
                    modified_time=row[2],
                    hash=row[3],
                    backed_up=bool(row[4]),
                    backup_time=row[5],
                    s3_key=row[6]
                ))
        return files
    
    def find_by_hash(self, file_hash: str) -> Optional[FileInfo]:
        """Find a backed-up file with the same hash (for deduplication)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT path, size, modified_time, hash, backed_up, backup_time, s3_key "
                "FROM files WHERE hash = ? AND backed_up = 1 AND s3_key IS NOT NULL "
                "LIMIT 1",
                (file_hash,)
            )
            row = cursor.fetchone()
            if row:
                return FileInfo(
                    path=row[0],
                    size=row[1],
                    modified_time=row[2],
                    hash=row[3],
                    backed_up=bool(row[4]),
                    backup_time=row[5],
                    s3_key=row[6]
                )
        return None
    
    def get_statistics(self) -> Dict:
        """Get backup statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    SUM(CASE WHEN backed_up = 1 THEN 1 ELSE 0 END) as backed_up_files,
                    SUM(size) as total_size,
                    SUM(CASE WHEN backed_up = 1 THEN size ELSE 0 END) as backed_up_size
                FROM files
            """)
            row = cursor.fetchone()
            return {
                'total_files': row[0] or 0,
                'backed_up_files': row[1] or 0,
                'pending_files': (row[0] or 0) - (row[1] or 0),
                'total_size': row[2] or 0,
                'backed_up_size': row[3] or 0
            }


class FileChangeHandler(FileSystemEventHandler):
    """
    Handler for file system events.
    
    Filters events and queues files for backup.
    """
    
    def __init__(
        self,
        scanner: 'FileScanner',
        on_change: Optional[Callable] = None
    ):
        super().__init__()
        self.scanner = scanner
        self.on_change = on_change
        self._pending_events: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        return self.scanner.should_exclude(path)
    
    def _handle_file_event(self, event, event_type: str):
        """Handle a file event."""
        if event.is_directory:
            return
        
        path = event.src_path
        if self._should_ignore(path):
            return
        
        # Debounce: only process if no event for this file in last 1 second
        now = datetime.now().timestamp()
        with self._lock:
            last_event = self._pending_events.get(path, 0)
            if now - last_event < 1.0:
                return
            self._pending_events[path] = now
        
        # Queue file for processing
        if event_type in ('created', 'modified'):
            self.scanner.queue_file(path)
        elif event_type == 'deleted':
            self.scanner.remove_file(path)
        
        # Callback
        if self.on_change:
            self.on_change(event_type, path)
    
    def on_created(self, event):
        self._handle_file_event(event, 'created')
    
    def on_modified(self, event):
        self._handle_file_event(event, 'modified')
    
    def on_deleted(self, event):
        self._handle_file_event(event, 'deleted')
    
    def on_moved(self, event):
        if event.is_directory:
            return
        
        # Handle as delete + create
        if not self._should_ignore(event.src_path):
            self.scanner.remove_file(event.src_path)
        
        if not self._should_ignore(event.dest_path):
            self.scanner.queue_file(event.dest_path)


class FileScanner:
    """
    File scanning and backup manager.
    
    Monitors specified directories, tracks changes, and uploads to S3.
    """
    
    def __init__(
        self,
        scan_paths: List[str],
        exclude_paths: List[str],
        exclude_patterns: List[str],
        s3_client: S3Client,
        hash_db_path: str,
        s3_prefix: str = "",
        max_file_size_mb: int = 500,
        min_file_size_bytes: int = 1,
        hash_algorithm: str = "sha256",
        on_file_backed_up: Optional[Callable] = None,
        on_file_changed: Optional[Callable] = None,
        on_error: Optional[Callable] = None
    ):
        self.scan_paths = [Path(p) for p in scan_paths]
        self.exclude_paths = [p.lower() for p in exclude_paths]
        self.exclude_patterns = [p.lower() for p in exclude_patterns]
        self.s3_client = s3_client
        self.s3_prefix = s3_prefix
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.min_file_size = min_file_size_bytes
        self.hash_algorithm = hash_algorithm
        
        # Callbacks
        self.on_file_backed_up = on_file_backed_up
        self.on_file_changed = on_file_changed
        self.on_error = on_error
        
        # Database
        self.hash_db = HashDatabase(hash_db_path)
        
        # File monitoring
        self.observer = Observer()
        self._running = False
        self._backup_queue: List[str] = []
        self._queue_lock = threading.Lock()
        self._backup_thread: Optional[threading.Thread] = None
    
    def should_exclude(self, path: str) -> bool:
        """Check if a path should be excluded from backup."""
        path_lower = path.lower()
        
        # Check exclude paths
        for exclude in self.exclude_paths:
            # Handle wildcards
            if '*' in exclude:
                # Convert to fnmatch pattern
                pattern = exclude.replace('\\', '/')
                path_check = path_lower.replace('\\', '/')
                if fnmatch.fnmatch(path_check, pattern):
                    return True
            else:
                # Prefix match
                if path_lower.startswith(exclude.rstrip('\\/')):
                    return True
        
        # Check filename patterns
        filename = os.path.basename(path_lower)
        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        
        return False
    
    def queue_file(self, path: str):
        """Add file to backup queue."""
        with self._queue_lock:
            if path not in self._backup_queue:
                self._backup_queue.append(path)
    
    def remove_file(self, path: str):
        """Remove file from tracking."""
        self.hash_db.remove_file(path)
        with self._queue_lock:
            if path in self._backup_queue:
                self._backup_queue.remove(path)
    
    def _get_s3_key(self, local_path: str) -> str:
        """Generate S3 key for a local file."""
        # Normalize path
        path = Path(local_path)
        
        # Create relative path from root
        # e.g., C:\Users\John\Documents\file.txt -> Users/John/Documents/file.txt
        parts = path.parts
        if len(parts) > 1 and ':' in parts[0]:
            # Windows path with drive letter
            relative = '/'.join(parts[1:])
        else:
            relative = '/'.join(parts)
        
        # Add prefix
        return f"{self.s3_prefix.rstrip('/')}/{relative}"
    
    def _process_file(self, path: str) -> bool:
        """
        Process a single file for backup.
        
        Returns True if file was backed up, False otherwise.
        """
        try:
            file_path = Path(path)
            
            # Check file exists
            if not file_path.exists():
                return False
            
            # Check file size
            stat = file_path.stat()
            if stat.st_size > self.max_file_size:
                return False  # Too large
            if stat.st_size < self.min_file_size:
                return False  # Too small (empty)
            
            # Calculate hash
            file_hash = calculate_file_hash(path, self.hash_algorithm)
            
            # Check if file has changed
            existing = self.hash_db.get_file(path)
            if existing and existing.hash == file_hash and existing.backed_up:
                # File unchanged and already backed up
                return True
            
            # Check for duplicate by hash (deduplication)
            duplicate = self.hash_db.find_by_hash(file_hash)
            if duplicate and duplicate.s3_key:
                # Same content already exists, just update database
                file_info = FileInfo(
                    path=path,
                    size=stat.st_size,
                    modified_time=stat.st_mtime,
                    hash=file_hash,
                    backed_up=True,
                    backup_time=datetime.now().timestamp(),
                    s3_key=duplicate.s3_key  # Reference existing S3 object
                )
                self.hash_db.upsert_file(file_info)
                return True
            
            # Upload to S3
            s3_key = self._get_s3_key(path)
            
            metadata = {
                'original-path': path,
                'file-hash': file_hash,
                'backup-time': datetime.now().isoformat()
            }
            
            success = self.s3_client.upload_file(
                path,
                s3_key,
                metadata=metadata
            )
            
            if success:
                # Update database
                file_info = FileInfo(
                    path=path,
                    size=stat.st_size,
                    modified_time=stat.st_mtime,
                    hash=file_hash,
                    backed_up=True,
                    backup_time=datetime.now().timestamp(),
                    s3_key=s3_key
                )
                self.hash_db.upsert_file(file_info)
                
                # Callback
                if self.on_file_backed_up:
                    self.on_file_backed_up(path, stat.st_size, s3_key)
                
                return True
            else:
                # Store file info but mark as not backed up
                file_info = FileInfo(
                    path=path,
                    size=stat.st_size,
                    modified_time=stat.st_mtime,
                    hash=file_hash,
                    backed_up=False
                )
                self.hash_db.upsert_file(file_info)
                return False
                
        except Exception as e:
            if self.on_error:
                self.on_error(path, str(e))
            return False
    
    def _backup_worker(self):
        """Background worker for processing backup queue."""
        while self._running:
            # Get next file from queue
            path = None
            with self._queue_lock:
                if self._backup_queue:
                    path = self._backup_queue.pop(0)
            
            if path:
                self._process_file(path)
            else:
                # No files in queue, sleep briefly
                threading.Event().wait(1.0)
    
    def start_monitoring(self):
        """Start file monitoring."""
        if self._running:
            return
        
        self._running = True
        
        # Setup watchdog observer
        handler = FileChangeHandler(
            self,
            on_change=self.on_file_changed
        )
        
        for scan_path in self.scan_paths:
            if scan_path.exists():
                self.observer.schedule(
                    handler,
                    str(scan_path),
                    recursive=True
                )
        
        self.observer.start()
        
        # Start backup worker
        self._backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
        self._backup_thread.start()
    
    def stop_monitoring(self):
        """Stop file monitoring."""
        self._running = False
        self.observer.stop()
        self.observer.join(timeout=5)
    
    def scan_all(self, callback: Optional[Callable[[str, int, int], None]] = None):
        """
        Perform full scan of all configured paths.
        
        Args:
            callback: Progress callback (path, files_scanned, total_files)
        """
        total_files = 0
        scanned = 0
        
        # Count files first
        for scan_path in self.scan_paths:
            if not scan_path.exists():
                continue
            for root, dirs, files in os.walk(scan_path):
                # Filter excluded directories
                dirs[:] = [d for d in dirs if not self.should_exclude(os.path.join(root, d))]
                total_files += len(files)
        
        # Scan files
        for scan_path in self.scan_paths:
            if not scan_path.exists():
                continue
            
            for root, dirs, files in os.walk(scan_path):
                # Filter excluded directories
                dirs[:] = [d for d in dirs if not self.should_exclude(os.path.join(root, d))]
                
                for filename in files:
                    file_path = os.path.join(root, filename)
                    
                    if not self.should_exclude(file_path):
                        self.queue_file(file_path)
                    
                    scanned += 1
                    if callback and scanned % 100 == 0:
                        callback(file_path, scanned, total_files)
        
        if callback:
            callback("", scanned, total_files)
    
    def get_statistics(self) -> Dict:
        """Get backup statistics."""
        stats = self.hash_db.get_statistics()
        with self._queue_lock:
            stats['queue_size'] = len(self._backup_queue)
        return stats
