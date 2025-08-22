"""
Storage Module

Unified storage abstraction supporting GCS, S3, and local filesystem
with consistent interface and advanced features like caching and compression.
"""

import gzip
import hashlib
import json
import mimetypes
import os
import pickle
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO, Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import urlparse

try:
    from google.cloud import storage as gcs

    HAS_GCS = True
except ImportError:
    HAS_GCS = False

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError

    HAS_S3 = True
except ImportError:
    HAS_S3 = False

from ..errors import ConfigurationError, SystemError
from ..logging import get_logger

logger = get_logger(__name__)


@dataclass
class StorageObject:
    """Represents a storage object with metadata."""

    key: str
    size: int
    last_modified: datetime
    content_type: Optional[str] = None
    etag: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "size": self.size,
            "last_modified": self.last_modified.isoformat(),
            "content_type": self.content_type,
            "etag": self.etag,
            "metadata": self.metadata or {},
        }


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Store an object."""
        pass

    @abstractmethod
    def get_object(self, key: str) -> Optional[bytes]:
        """Retrieve an object."""
        pass

    @abstractmethod
    def delete_object(self, key: str) -> bool:
        """Delete an object."""
        pass

    @abstractmethod
    def list_objects(
        self, prefix: str = "", limit: Optional[int] = None
    ) -> List[StorageObject]:
        """List objects with optional prefix filter."""
        pass

    @abstractmethod
    def object_exists(self, key: str) -> bool:
        """Check if an object exists."""
        pass

    @abstractmethod
    def get_object_metadata(self, key: str) -> Optional[StorageObject]:
        """Get object metadata."""
        pass

    @abstractmethod
    def generate_presigned_url(
        self, key: str, expiration: int = 3600, method: str = "GET"
    ) -> Optional[str]:
        """Generate a presigned URL for temporary access."""
        pass


class GCSBackend(StorageBackend):
    """Google Cloud Storage backend."""

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        if not HAS_GCS:
            raise ConfigurationError("Google Cloud Storage library not available")

        self.bucket_name = bucket_name
        self.project_id = project_id

        try:
            self.client = gcs.Client(project=project_id)
            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"Initialized GCS backend: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize GCS backend: {e}")
            raise ConfigurationError(f"GCS initialization failed: {e}")

    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Store object in GCS."""
        try:
            blob = self.bucket.blob(key)

            if content_type:
                blob.content_type = content_type
            elif isinstance(data, bytes):
                blob.content_type = (
                    mimetypes.guess_type(key)[0] or "application/octet-stream"
                )

            if metadata:
                blob.metadata = metadata

            if isinstance(data, bytes):
                blob.upload_from_string(data)
            else:
                blob.upload_from_file(data)

            logger.debug(f"Uploaded object to GCS: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload object {key} to GCS: {e}")
            return False

    def get_object(self, key: str) -> Optional[bytes]:
        """Retrieve object from GCS."""
        try:
            blob = self.bucket.blob(key)
            if not blob.exists():
                return None

            data = blob.download_as_bytes()
            logger.debug(f"Downloaded object from GCS: {key}")
            return data
        except Exception as e:
            logger.error(f"Failed to download object {key} from GCS: {e}")
            return None

    def delete_object(self, key: str) -> bool:
        """Delete object from GCS."""
        try:
            blob = self.bucket.blob(key)
            blob.delete()
            logger.debug(f"Deleted object from GCS: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete object {key} from GCS: {e}")
            return False

    def list_objects(
        self, prefix: str = "", limit: Optional[int] = None
    ) -> List[StorageObject]:
        """List objects in GCS bucket."""
        try:
            blobs = self.client.list_blobs(
                self.bucket, prefix=prefix, max_results=limit
            )

            objects = []
            for blob in blobs:
                obj = StorageObject(
                    key=blob.name,
                    size=blob.size or 0,
                    last_modified=blob.time_created or datetime.now(),
                    content_type=blob.content_type,
                    etag=blob.etag,
                    metadata=blob.metadata,
                )
                objects.append(obj)

            logger.debug(
                f"Listed {len(objects)} objects from GCS with prefix: {prefix}"
            )
            return objects
        except Exception as e:
            logger.error(f"Failed to list objects from GCS: {e}")
            return []

    def object_exists(self, key: str) -> bool:
        """Check if object exists in GCS."""
        try:
            blob = self.bucket.blob(key)
            return blob.exists()
        except Exception as e:
            logger.error(f"Failed to check object existence {key} in GCS: {e}")
            return False

    def get_object_metadata(self, key: str) -> Optional[StorageObject]:
        """Get object metadata from GCS."""
        try:
            blob = self.bucket.blob(key)
            if not blob.exists():
                return None

            blob.reload()
            return StorageObject(
                key=blob.name,
                size=blob.size or 0,
                last_modified=blob.time_created or datetime.now(),
                content_type=blob.content_type,
                etag=blob.etag,
                metadata=blob.metadata,
            )
        except Exception as e:
            logger.error(f"Failed to get metadata for {key} from GCS: {e}")
            return None

    def generate_presigned_url(
        self, key: str, expiration: int = 3600, method: str = "GET"
    ) -> Optional[str]:
        """Generate presigned URL for GCS object."""
        try:
            blob = self.bucket.blob(key)
            url = blob.generate_signed_url(
                version="v4", expiration=timedelta(seconds=expiration), method=method
            )
            logger.debug(f"Generated presigned URL for GCS object: {key}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            return None


class S3Backend(StorageBackend):
    """Amazon S3 backend."""

    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        if not HAS_S3:
            raise ConfigurationError("AWS S3 library not available")

        self.bucket_name = bucket_name
        self.region = region

        try:
            self.client = boto3.client(
                "s3",
                region_name=region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
            logger.info(f"Initialized S3 backend: {bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 backend: {e}")
            raise ConfigurationError(f"S3 initialization failed: {e}")

    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Store object in S3."""
        try:
            put_args = {"Bucket": self.bucket_name, "Key": key, "Body": data}

            if content_type:
                put_args["ContentType"] = content_type

            if metadata:
                put_args["Metadata"] = metadata

            self.client.put_object(**put_args)
            logger.debug(f"Uploaded object to S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload object {key} to S3: {e}")
            return False

    def get_object(self, key: str) -> Optional[bytes]:
        """Retrieve object from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            data = response["Body"].read()
            logger.debug(f"Downloaded object from S3: {key}")
            return data
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return None
            logger.error(f"Failed to download object {key} from S3: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to download object {key} from S3: {e}")
            return None

    def delete_object(self, key: str) -> bool:
        """Delete object from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.debug(f"Deleted object from S3: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete object {key} from S3: {e}")
            return False

    def list_objects(
        self, prefix: str = "", limit: Optional[int] = None
    ) -> List[StorageObject]:
        """List objects in S3 bucket."""
        try:
            list_args = {"Bucket": self.bucket_name, "Prefix": prefix}

            if limit:
                list_args["MaxKeys"] = limit

            response = self.client.list_objects_v2(**list_args)

            objects = []
            for obj in response.get("Contents", []):
                storage_obj = StorageObject(
                    key=obj["Key"],
                    size=obj["Size"],
                    last_modified=obj["LastModified"],
                    etag=obj["ETag"],
                )
                objects.append(storage_obj)

            logger.debug(f"Listed {len(objects)} objects from S3 with prefix: {prefix}")
            return objects
        except Exception as e:
            logger.error(f"Failed to list objects from S3: {e}")
            return []

    def object_exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Failed to check object existence {key} in S3: {e}")
            return False

    def get_object_metadata(self, key: str) -> Optional[StorageObject]:
        """Get object metadata from S3."""
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=key)
            return StorageObject(
                key=key,
                size=response["ContentLength"],
                last_modified=response["LastModified"],
                content_type=response.get("ContentType"),
                etag=response["ETag"],
                metadata=response.get("Metadata", {}),
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            logger.error(f"Failed to get metadata for {key} from S3: {e}")
            return None

    def generate_presigned_url(
        self, key: str, expiration: int = 3600, method: str = "GET"
    ) -> Optional[str]:
        """Generate presigned URL for S3 object."""
        try:
            method_map = {
                "GET": "get_object",
                "PUT": "put_object",
                "DELETE": "delete_object",
            }

            operation = method_map.get(method.upper(), "get_object")

            url = self.client.generate_presigned_url(
                operation,
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            logger.debug(f"Generated presigned URL for S3 object: {key}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {key}: {e}")
            return None


class LocalBackend(StorageBackend):
    """Local filesystem backend."""

    def __init__(self, base_path: str = "./storage"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized local storage backend: {self.base_path}")

    def _get_file_path(self, key: str) -> Path:
        """Get full file path for key."""
        return self.base_path / key

    def put_object(
        self,
        key: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """Store object locally."""
        try:
            file_path = self._get_file_path(key)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if isinstance(data, bytes):
                file_path.write_bytes(data)
            else:
                with open(file_path, "wb") as f:
                    if hasattr(data, "read"):
                        f.write(data.read())
                    else:
                        f.write(data)

            # Store metadata in separate file
            if metadata:
                metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
                metadata_path.write_text(json.dumps(metadata))

            logger.debug(f"Stored object locally: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store object {key} locally: {e}")
            return False

    def get_object(self, key: str) -> Optional[bytes]:
        """Retrieve object from local storage."""
        try:
            file_path = self._get_file_path(key)
            if not file_path.exists():
                return None

            data = file_path.read_bytes()
            logger.debug(f"Retrieved object locally: {key}")
            return data
        except Exception as e:
            logger.error(f"Failed to retrieve object {key} locally: {e}")
            return None

    def delete_object(self, key: str) -> bool:
        """Delete object from local storage."""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()

            # Delete metadata file if exists
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
            if metadata_path.exists():
                metadata_path.unlink()

            logger.debug(f"Deleted object locally: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete object {key} locally: {e}")
            return False

    def list_objects(
        self, prefix: str = "", limit: Optional[int] = None
    ) -> List[StorageObject]:
        """List objects in local storage."""
        try:
            objects = []
            search_path = self.base_path / prefix if prefix else self.base_path

            if search_path.is_file():
                # Single file
                stat = search_path.stat()
                rel_path = search_path.relative_to(self.base_path)
                obj = StorageObject(
                    key=str(rel_path),
                    size=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime),
                )
                objects.append(obj)
            else:
                # Directory or glob pattern
                pattern = "**/*" if not prefix else f"{prefix}*"
                for file_path in self.base_path.glob(pattern):
                    if file_path.is_file() and not file_path.name.endswith(".meta"):
                        stat = file_path.stat()
                        rel_path = file_path.relative_to(self.base_path)
                        obj = StorageObject(
                            key=str(rel_path),
                            size=stat.st_size,
                            last_modified=datetime.fromtimestamp(stat.st_mtime),
                        )
                        objects.append(obj)

                        if limit and len(objects) >= limit:
                            break

            logger.debug(f"Listed {len(objects)} objects locally with prefix: {prefix}")
            return objects
        except Exception as e:
            logger.error(f"Failed to list objects locally: {e}")
            return []

    def object_exists(self, key: str) -> bool:
        """Check if object exists locally."""
        file_path = self._get_file_path(key)
        return file_path.exists()

    def get_object_metadata(self, key: str) -> Optional[StorageObject]:
        """Get object metadata from local storage."""
        try:
            file_path = self._get_file_path(key)
            if not file_path.exists():
                return None

            stat = file_path.stat()

            # Load metadata if exists
            metadata = None
            metadata_path = file_path.with_suffix(file_path.suffix + ".meta")
            if metadata_path.exists():
                metadata = json.loads(metadata_path.read_text())

            return StorageObject(
                key=key,
                size=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                content_type=mimetypes.guess_type(str(file_path))[0],
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to get metadata for {key} locally: {e}")
            return None

    def generate_presigned_url(
        self, key: str, expiration: int = 3600, method: str = "GET"
    ) -> Optional[str]:
        """Generate file URL for local storage (not truly presigned)."""
        file_path = self._get_file_path(key)
        if file_path.exists():
            return f"file://{file_path.absolute()}"
        return None


class Storage:
    """
    Unified storage interface with caching and compression support.
    """

    def __init__(
        self,
        backend: StorageBackend,
        enable_compression: bool = False,
        cache_size: int = 100,
    ):
        self.backend = backend
        self.enable_compression = enable_compression
        self._cache: Dict[str, Tuple[bytes, datetime]] = {}
        self._cache_size = cache_size
        self._cache_lock = threading.Lock()

    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data)

    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress data using gzip."""
        try:
            return gzip.decompress(data)
        except gzip.BadGzipFile:
            # Data is not compressed
            return data

    def _cache_get(self, key: str) -> Optional[bytes]:
        """Get data from cache."""
        with self._cache_lock:
            if key in self._cache:
                data, timestamp = self._cache[key]
                # Simple TTL of 5 minutes
                if datetime.now() - timestamp < timedelta(minutes=5):
                    logger.debug(f"Cache hit for: {key}")
                    return data
                else:
                    del self._cache[key]
        return None

    def _cache_put(self, key: str, data: bytes) -> None:
        """Put data in cache."""
        with self._cache_lock:
            # Simple LRU eviction
            if len(self._cache) >= self._cache_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]

            self._cache[key] = (data, datetime.now())
            logger.debug(f"Cached data for: {key}")

    def put(
        self,
        key: str,
        data: Union[bytes, str, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        compress: Optional[bool] = None,
    ) -> bool:
        """Store data in storage."""
        try:
            # Convert string to bytes
            if isinstance(data, str):
                data = data.encode("utf-8")
                if content_type is None:
                    content_type = "text/plain; charset=utf-8"

            # Apply compression if enabled
            should_compress = (
                compress if compress is not None else self.enable_compression
            )
            if should_compress and isinstance(data, bytes):
                data = self._compress_data(data)
                if metadata is None:
                    metadata = {}
                metadata["compressed"] = "gzip"

            success = self.backend.put_object(key, data, content_type, metadata)

            # Cache the original (uncompressed) data
            if success and isinstance(data, bytes):
                original_data = self._decompress_data(data) if should_compress else data
                self._cache_put(key, original_data)

            return success
        except Exception as e:
            logger.error(f"Failed to put object {key}: {e}")
            return False

    def get(self, key: str, use_cache: bool = True) -> Optional[bytes]:
        """Retrieve data from storage."""
        try:
            # Check cache first
            if use_cache:
                cached_data = self._cache_get(key)
                if cached_data is not None:
                    return cached_data

            data = self.backend.get_object(key)
            if data is None:
                return None

            # Check if data is compressed
            metadata = self.backend.get_object_metadata(key)
            if (
                metadata
                and metadata.metadata
                and metadata.metadata.get("compressed") == "gzip"
            ):
                data = self._decompress_data(data)

            # Cache the data
            if use_cache:
                self._cache_put(key, data)

            return data
        except Exception as e:
            logger.error(f"Failed to get object {key}: {e}")
            return None

    def get_text(
        self, key: str, encoding: str = "utf-8", use_cache: bool = True
    ) -> Optional[str]:
        """Retrieve text data from storage."""
        data = self.get(key, use_cache)
        if data is None:
            return None

        try:
            return data.decode(encoding)
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode text for {key}: {e}")
            return None

    def get_json(self, key: str, use_cache: bool = True) -> Optional[Any]:
        """Retrieve JSON data from storage."""
        text = self.get_text(key, use_cache=use_cache)
        if text is None:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for {key}: {e}")
            return None

    def put_text(self, key: str, text: str, encoding: str = "utf-8", **kwargs) -> bool:
        """Store text data."""
        return self.put(
            key,
            text.encode(encoding),
            content_type="text/plain; charset=utf-8",
            **kwargs,
        )

    def put_json(self, key: str, data: Any, **kwargs) -> bool:
        """Store JSON data."""
        try:
            json_text = json.dumps(data, ensure_ascii=False, indent=2)
            return self.put(key, json_text, content_type="application/json", **kwargs)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize JSON for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete data from storage."""
        # Remove from cache
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]

        return self.backend.delete_object(key)

    def exists(self, key: str) -> bool:
        """Check if object exists."""
        return self.backend.object_exists(key)

    def list(
        self, prefix: str = "", limit: Optional[int] = None
    ) -> List[StorageObject]:
        """List objects."""
        return self.backend.list_objects(prefix, limit)

    def get_metadata(self, key: str) -> Optional[StorageObject]:
        """Get object metadata."""
        return self.backend.get_object_metadata(key)

    def generate_url(
        self, key: str, expiration: int = 3600, method: str = "GET"
    ) -> Optional[str]:
        """Generate presigned URL."""
        return self.backend.generate_presigned_url(key, expiration, method)

    def copy(self, src_key: str, dst_key: str) -> bool:
        """Copy object within storage."""
        data = self.get(src_key, use_cache=False)
        if data is None:
            return False

        metadata = self.get_metadata(src_key)
        return self.put(
            dst_key,
            data,
            content_type=metadata.content_type if metadata else None,
            metadata=metadata.metadata if metadata else None,
        )

    def clear_cache(self) -> None:
        """Clear the cache."""
        with self._cache_lock:
            self._cache.clear()
            logger.info("Storage cache cleared")


def create_storage(backend_type: str, **kwargs) -> Storage:
    """
    Factory function to create storage instance.

    Args:
        backend_type: Type of backend ('gcs', 's3', 'local')
        **kwargs: Backend-specific configuration

    Returns:
        Storage instance
    """
    backend_type = backend_type.lower()

    if backend_type == "gcs":
        backend = GCSBackend(**kwargs)
    elif backend_type == "s3":
        backend = S3Backend(**kwargs)
    elif backend_type == "local":
        backend = LocalBackend(**kwargs)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")

    storage_kwargs = {
        k: v for k, v in kwargs.items() if k in ["enable_compression", "cache_size"]
    }
    return Storage(backend, **storage_kwargs)
