"""
AWS S3 Client for Endpoint Security Agent

Handles all S3 operations including:
- Multipart uploads for large files
- Bandwidth throttling
- Progress tracking
- Error handling with retries
"""

import os
import hashlib
import threading
import time
from pathlib import Path
from typing import Callable, Dict, Optional, BinaryIO
from dataclasses import dataclass
from datetime import datetime

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from boto3.s3.transfer import TransferConfig


@dataclass
class UploadProgress:
    """Track upload progress."""
    filename: str
    total_bytes: int
    uploaded_bytes: int = 0
    start_time: float = 0
    
    @property
    def percentage(self) -> float:
        if self.total_bytes == 0:
            return 100.0
        return (self.uploaded_bytes / self.total_bytes) * 100
    
    @property
    def speed_mbps(self) -> float:
        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0
        return (self.uploaded_bytes / elapsed) / (1024 * 1024)


class ThrottledUpload:
    """Wrapper for throttled file uploads."""
    
    def __init__(self, file_obj: BinaryIO, max_mbps: float):
        self.file_obj = file_obj
        self.max_bytes_per_sec = max_mbps * 1024 * 1024
        self.bytes_sent = 0
        self.start_time = time.time()
    
    def read(self, size: int = -1) -> bytes:
        # Calculate how much we should have sent by now
        elapsed = time.time() - self.start_time
        allowed_bytes = int(elapsed * self.max_bytes_per_sec)
        
        # If we're ahead, wait
        if self.bytes_sent >= allowed_bytes:
            sleep_time = (self.bytes_sent - allowed_bytes) / self.max_bytes_per_sec
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        data = self.file_obj.read(size)
        self.bytes_sent += len(data)
        return data
    
    def seek(self, *args, **kwargs):
        return self.file_obj.seek(*args, **kwargs)
    
    def tell(self):
        return self.file_obj.tell()


class S3Client:
    """
    S3 client with support for large file uploads and throttling.
    """
    
    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        storage_class: str = "STANDARD_IA",
        max_mbps: Optional[float] = None
    ):
        self.bucket = bucket
        self.region = region
        self.storage_class = storage_class
        self.max_mbps = max_mbps
        
        # Configure boto3 client
        boto_config = BotoConfig(
            region_name=region,
            retries={'max_attempts': 5, 'mode': 'adaptive'},
            max_pool_connections=50
        )
        
        # Create client with or without explicit credentials
        client_kwargs = {'config': boto_config}
        if access_key_id and secret_access_key:
            client_kwargs['aws_access_key_id'] = access_key_id
            client_kwargs['aws_secret_access_key'] = secret_access_key
        
        self.client = boto3.client('s3', **client_kwargs)
        self.resource = boto3.resource('s3', **client_kwargs)
        
        # Transfer configuration for multipart uploads
        self.transfer_config = TransferConfig(
            multipart_threshold=8 * 1024 * 1024,  # 8MB
            max_concurrency=10,
            multipart_chunksize=8 * 1024 * 1024,  # 8MB chunks
            use_threads=True
        )
        
        # Progress tracking
        self._progress: Dict[str, UploadProgress] = {}
        self._lock = threading.Lock()
    
    def upload_file(
        self,
        local_path: str,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> bool:
        """
        Upload a file to S3 with multipart support.
        
        Args:
            local_path: Path to local file
            s3_key: S3 object key
            metadata: Optional metadata to attach
            progress_callback: Optional callback for progress updates
            
        Returns:
            True if upload successful, False otherwise
        """
        try:
            file_path = Path(local_path)
            if not file_path.exists():
                return False
            
            file_size = file_path.stat().st_size
            
            # Initialize progress tracking
            progress = UploadProgress(
                filename=file_path.name,
                total_bytes=file_size,
                start_time=time.time()
            )
            
            with self._lock:
                self._progress[s3_key] = progress
            
            # Prepare extra args
            extra_args = {
                'StorageClass': self.storage_class
            }
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Create progress callback wrapper
            def update_progress(bytes_transferred: int):
                progress.uploaded_bytes = bytes_transferred
                if progress_callback:
                    progress_callback(progress)
            
            # Upload with or without throttling
            if self.max_mbps and self.max_mbps > 0:
                # Throttled upload (manual multipart)
                self._upload_throttled(local_path, s3_key, extra_args, update_progress)
            else:
                # Standard upload with boto3 transfer manager
                self.client.upload_file(
                    local_path,
                    self.bucket,
                    s3_key,
                    Config=self.transfer_config,
                    ExtraArgs=extra_args,
                    Callback=update_progress
                )
            
            return True
            
        except ClientError as e:
            print(f"S3 upload error: {e}")
            return False
        except Exception as e:
            print(f"Upload error: {e}")
            return False
        finally:
            with self._lock:
                self._progress.pop(s3_key, None)
    
    def _upload_throttled(
        self,
        local_path: str,
        s3_key: str,
        extra_args: Dict,
        progress_callback: Callable
    ):
        """Upload with bandwidth throttling."""
        file_size = os.path.getsize(local_path)
        chunk_size = 8 * 1024 * 1024  # 8MB
        
        # Small files: simple put
        if file_size <= chunk_size:
            with open(local_path, 'rb') as f:
                throttled = ThrottledUpload(f, self.max_mbps)
                data = throttled.read()
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=s3_key,
                    Body=data,
                    **extra_args
                )
                progress_callback(file_size)
            return
        
        # Large files: multipart upload
        mpu = self.client.create_multipart_upload(
            Bucket=self.bucket,
            Key=s3_key,
            **extra_args
        )
        upload_id = mpu['UploadId']
        
        try:
            parts = []
            uploaded = 0
            part_number = 1
            
            with open(local_path, 'rb') as f:
                throttled = ThrottledUpload(f, self.max_mbps)
                
                while True:
                    data = throttled.read(chunk_size)
                    if not data:
                        break
                    
                    # Upload part
                    response = self.client.upload_part(
                        Bucket=self.bucket,
                        Key=s3_key,
                        PartNumber=part_number,
                        UploadId=upload_id,
                        Body=data
                    )
                    
                    parts.append({
                        'PartNumber': part_number,
                        'ETag': response['ETag']
                    })
                    
                    uploaded += len(data)
                    progress_callback(uploaded)
                    part_number += 1
            
            # Complete multipart upload
            self.client.complete_multipart_upload(
                Bucket=self.bucket,
                Key=s3_key,
                UploadId=upload_id,
                MultipartUpload={'Parts': parts}
            )
            
        except Exception:
            # Abort on failure
            self.client.abort_multipart_upload(
                Bucket=self.bucket,
                Key=s3_key,
                UploadId=upload_id
            )
            raise
    
    def download_file(self, s3_key: str, local_path: str) -> bool:
        """Download a file from S3."""
        try:
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(self.bucket, s3_key, local_path)
            return True
        except ClientError:
            return False
    
    def file_exists(self, s3_key: str) -> bool:
        """Check if a file exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False
    
    def get_file_hash(self, s3_key: str) -> Optional[str]:
        """Get the ETag (hash) of an S3 object."""
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return response['ETag'].strip('"')
        except ClientError:
            return None
    
    def list_objects(self, prefix: str = "") -> list:
        """List objects in the bucket with given prefix."""
        objects = []
        paginator = self.client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"')
                })
        
        return objects
    
    def delete_object(self, s3_key: str) -> bool:
        """Delete an object from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError:
            return False
    
    def get_bucket_size(self, prefix: str = "") -> int:
        """Get total size of objects with given prefix."""
        total = 0
        for obj in self.list_objects(prefix):
            total += obj['size']
        return total


def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> str:
    """Calculate hash of a file."""
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()
