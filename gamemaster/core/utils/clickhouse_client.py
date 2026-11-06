"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

ClickHouse-backed object storage client for GameMaster.

This client stores IIDM, DSL, and metadata artifacts inside a ClickHouse table
while exposing a small object-store-like API (upload/get/list/delete/stat).
"""

from __future__ import annotations

import base64
import datetime as dt
import logging
import os
import re
from functools import lru_cache
from typing import Generator, Optional

import clickhouse_connect

logger = logging.getLogger(__name__)

DEFAULT_IIDM_BUCKET = "iidm-files"
DEFAULT_DSL_BUCKET = "dsl-files"


class StorageError(Exception):
    """Generic storage error with optional code attribute."""

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code or ""


class StorageNotFound(StorageError):
    """Raised when an object does not exist."""

    def __init__(self, message: str = "Object not found", code: str | None = None):
        super().__init__(message, code=code or "NoSuchKey")


class StorageObject:
    """Lightweight representation of a stored object for list/stat operations."""

    def __init__(
        self,
        object_name: str,
        size: int = 0,
        last_modified: Optional[dt.datetime] = None,
        etag: Optional[str] = None,
    ):
        self.object_name = object_name
        self.size = size
        self.last_modified = last_modified
        self.etag = etag


# Valid ClickHouse identifier pattern (alphanumeric and underscores only)
_VALID_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _validate_identifier(name: str, label: str = "identifier") -> str:
    """Validate that a name is safe for use as a ClickHouse identifier."""
    if not name or not _VALID_IDENTIFIER_RE.match(name):
        raise ValueError(
            f"Invalid {label}: '{name}'. Must be alphanumeric with underscores only."
        )
    return name


class ClickhouseClient:
    """ClickHouse-backed artifact storage."""

    def __init__(self):
        self.host = os.getenv("CLICKHOUSE_HOST", "localhost")
        self.port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
        user_env = os.getenv("CLICKHOUSE_USERNAME") or os.getenv("CLICKHOUSE_USER")
        self.username = user_env or ""
        self.password = os.getenv("CLICKHOUSE_PASSWORD", "")
        self.database = _validate_identifier(
            os.getenv("CLICKHOUSE_DATABASE", "gamemaster"), "database name"
        )
        self.secure = str(os.getenv("CLICKHOUSE_SECURE", "false")).lower() in {
            "1",
            "true",
            "yes",
        }
        self.timeout = int(os.getenv("CLICKHOUSE_TIMEOUT_SECONDS", "10"))

        self.bucket_name = os.getenv("GAMEMASTER_IIDM_BUCKET", DEFAULT_IIDM_BUCKET)
        self.dsl_bucket = os.getenv("GAMEMASTER_DSL_BUCKET", DEFAULT_DSL_BUCKET)

        self.client = self._init_client()
        self._ensure_schema()

    def _init_client(self):
        """Initialize a ClickHouse client, bootstrapping the database if needed."""
        try:
            return clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username or None,
                password=self.password or None,
                database=self.database,
                secure=self.secure,
                connect_timeout=self.timeout,
            )
        except Exception:
            bootstrap = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username or None,
                password=self.password or None,
                secure=self.secure,
                connect_timeout=self.timeout,
            )
            bootstrap.command(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            bootstrap.close()
            return clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.username or None,
                password=self.password or None,
                database=self.database,
                secure=self.secure,
                connect_timeout=self.timeout,
            )

    # ---------------------- Internal helpers ----------------------
    def _full_path(self, file_name: str, bucket_name: Optional[str]) -> str:
        bucket = bucket_name or self.bucket_name
        return f"{bucket}/{file_name}"

    def _ensure_schema(self) -> None:
        """Create database and storage table when missing."""
        self.client.command(f"CREATE DATABASE IF NOT EXISTS {self.database}")
        # Use DateTime64(6) for microsecond precision to avoid race conditions
        # when delete+upload happen within the same second.
        self.client.command(
            f"""
            CREATE TABLE IF NOT EXISTS {self.database}.file_storage (
                bucket String,
                file_path String,
                content_base64 String,
                content_type String,
                file_size UInt64,
                created_at DateTime64(6) DEFAULT now64(6),
                updated_at DateTime64(6) DEFAULT now64(6),
                is_deleted UInt8 DEFAULT 0
            )
            ENGINE = ReplacingMergeTree(updated_at)
            ORDER BY (bucket, file_path)
            """
        )

    def _parse_datetime(self, value) -> Optional[dt.datetime]:
        if value is None:
            return None
        try:
            if isinstance(value, dt.datetime):
                return value
            return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    def _now_microseconds(self) -> dt.datetime:
        """Return current UTC time with microsecond precision."""
        return dt.datetime.now(dt.timezone.utc)

    # ---------------------- Public API ----------------------
    def check_bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """Best-effort health check."""
        try:
            self.health_check()
            return True
        except Exception:
            return False

    def _ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> None:
        """Buckets are logical; nothing to create."""
        pass

    def upload_file(
        self,
        file_name: str,
        file_data,
        bucket_name: Optional[str] = None,
        size: Optional[int] = None,
    ) -> None:
        """Store or replace an object."""
        if isinstance(file_data, (bytes, bytearray, memoryview)):
            content = bytes(file_data)
        else:
            content = file_data.read()
        if content is None:
            content = b""
        file_size = len(content) if size is None else size
        content_type = (
            "application/xml"
            if file_name.endswith((".iidm", ".xiidm", ".xml"))
            else ("application/json" if file_name.endswith(".json") else "text/plain")
        )
        encoded = base64.b64encode(content).decode("utf-8")

        bucket = bucket_name or self.bucket_name
        full_path = self._full_path(file_name, bucket_name)
        now = self._now_microseconds()

        try:
            self.client.insert(
                f"{self.database}.file_storage",
                [
                    [
                        bucket,
                        full_path,
                        encoded,
                        content_type,
                        file_size,
                        now,
                        now,
                        0,
                    ]
                ],
                column_names=[
                    "bucket",
                    "file_path",
                    "content_base64",
                    "content_type",
                    "file_size",
                    "created_at",
                    "updated_at",
                    "is_deleted",
                ],
            )
            logger.debug("Uploaded file '%s' to bucket '%s'", file_name, bucket)
        except Exception as exc:
            raise StorageError(f"Failed to upload '{file_name}': {exc}")

    def get_file(self, file_name: str, bucket_name: Optional[str] = None) -> bytes:
        """Return raw bytes for the given object."""
        bucket = bucket_name or self.bucket_name
        full_path = self._full_path(file_name, bucket_name)
        query = f"""
        SELECT content_base64
        FROM {self.database}.file_storage FINAL
        WHERE bucket=%(bucket)s AND file_path=%(path)s AND is_deleted=0
        ORDER BY updated_at DESC
        LIMIT 1
        """
        try:
            result = self.client.query(
                query, parameters={"bucket": bucket, "path": full_path}
            )
        except Exception as exc:
            raise StorageError(f"Failed to query '{file_name}': {exc}")

        rows = result.result_rows
        if not rows:
            raise StorageNotFound(f"{file_name} not found in {bucket}")
        encoded = rows[0][0]
        try:
            data = base64.b64decode(encoded)
            logger.debug("Retrieved file '%s' from bucket '%s'", file_name, bucket)
            return data
        except Exception as exc:
            raise StorageError(f"Failed to decode stored content: {exc}")

    def stat_object(self, bucket_name: str, file_name: str) -> StorageObject:
        """Return metadata for a single object."""
        full_path = self._full_path(file_name, bucket_name)
        query = f"""
        SELECT file_size, updated_at
        FROM {self.database}.file_storage FINAL
        WHERE bucket=%(bucket)s AND file_path=%(path)s AND is_deleted=0
        ORDER BY updated_at DESC
        LIMIT 1
        """
        try:
            result = self.client.query(
                query, parameters={"bucket": bucket_name, "path": full_path}
            )
        except Exception as exc:
            raise StorageError(f"Failed to stat '{file_name}': {exc}")

        rows = result.result_rows
        if not rows:
            raise StorageNotFound(f"{file_name} not found in {bucket_name}")
        size = int(rows[0][0] or 0)
        last_modified = self._parse_datetime(rows[0][1])
        return StorageObject(
            object_name=file_name, size=size, last_modified=last_modified
        )

    def list_objects(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        recursive: bool = True,
    ) -> Generator[StorageObject, None, None]:
        """Yield objects matching a prefix within the bucket.

        Note: The `recursive` parameter is accepted for API compatibility but
        this implementation always lists recursively.
        """
        full_prefix = self._full_path(prefix or "", bucket_name)
        query = f"""
        SELECT file_path, file_size, updated_at
        FROM {self.database}.file_storage FINAL
        WHERE bucket=%(bucket)s AND is_deleted=0 AND startsWith(file_path, %(prefix)s)
        ORDER BY file_path ASC
        """
        try:
            rows = self.client.query(
                query, parameters={"bucket": bucket_name, "prefix": full_prefix}
            ).result_rows
        except Exception as exc:
            raise StorageError(f"Failed to list objects with prefix '{prefix}': {exc}")

        if not rows:
            return iter(())
        objects = []
        for file_path, file_size, updated_at in rows:
            object_name = file_path.split("/", 1)[1] if "/" in file_path else file_path
            objects.append(
                StorageObject(
                    object_name=object_name,
                    size=int(file_size or 0),
                    last_modified=self._parse_datetime(updated_at),
                )
            )
        return iter(objects)

    def remove_object(self, bucket_name: str, file_name: str) -> None:
        """Delete an object by inserting a tombstone row."""
        full_path = self._full_path(file_name, bucket_name)
        now = self._now_microseconds()
        try:
            self.client.insert(
                f"{self.database}.file_storage",
                [
                    [
                        bucket_name,
                        full_path,
                        "",
                        "",
                        0,
                        now,
                        now,
                        1,
                    ]
                ],
                column_names=[
                    "bucket",
                    "file_path",
                    "content_base64",
                    "content_type",
                    "file_size",
                    "created_at",
                    "updated_at",
                    "is_deleted",
                ],
            )
            logger.debug("Deleted file '%s' from bucket '%s'", file_name, bucket_name)
        except Exception as exc:
            raise StorageError(f"Failed to delete '{file_name}': {exc}")

    def health_check(self) -> bool:
        """Lightweight liveness test."""
        self.client.query("SELECT 1")
        return True

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass


@lru_cache(maxsize=1)
def get_clickhouse_client() -> ClickhouseClient:
    """Return a cached ClickHouse client instance."""
    return ClickhouseClient()


__all__ = [
    "ClickhouseClient",
    "StorageError",
    "StorageNotFound",
    "StorageObject",
    "get_clickhouse_client",
]
