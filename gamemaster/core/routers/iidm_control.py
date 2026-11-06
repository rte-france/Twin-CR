#!/usr/bin/env python3Query
"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

"""
IIDM (Interoperable Intelligent Distribution Model) upload and fetch API.

The router exposes endpoints to store IIDM artifacts in the ClickHouse-backed
object storage, maintain metadata, and serve cached network properties for
downstream services.
"""

import logging
import os
import tempfile
import uuid
from asyncio import to_thread
from datetime import datetime, timezone
from typing import Optional

import orjson
import pypowsybl.network as pn
from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    File,
    Response,
    Cookie,
    Path,
    Query,
)
from retrying import retry

from ..utils.iidm_helper import extract_network_data, serialize_network_data
from ..utils.clickhouse_client import (
    StorageError,
    StorageNotFound,
    get_clickhouse_client,
)

# Module-level logger; configuration is handled by the application entry point
logger = logging.getLogger(__name__)

router = APIRouter(tags=["IIDM Control"])
BUCKET_NAME = "iidm-files"


def retry_if_storage_error(exception):
    """
    Determine whether a retry should occur for a storage operation.

    Args:
        exception (Exception): Error raised by a storage client call.

    Returns:
        bool: ``True`` when the exception originates from the storage client.
    """
    if not isinstance(exception, StorageError):
        return False
    code = getattr(exception, "code", "") or ""
    return code not in ("NoSuchKey", "NoSuchObject")


def _storage_client():
    """
    Return the shared storage client wrapper configured for IIDM storage.

    Returns:
        StorageClient: Helper that knows the bucket name and credentials.
    """
    return get_clickhouse_client()


@router.post("/iidm/upload")
async def upload_iidm_file(
    response: Response,
    file: UploadFile = File(...),
    artifact_id: Optional[str] = Query(
        None,
        description="Optional artifact_id to also store cached network data under <artifact_id>/network_data.json",
    ),
    description: Optional[str] = Query(
        None,
        description="Optional human-friendly description stored alongside the IIDM metadata",
    ),
):
    """
    Upload and validate an IIDM file, store to the ClickHouse-backed object
    storage, and set iidm_file_id cookie.
    """
    fname = file.filename.lower()

    # Get prefix and suffix from filename to determine if compressed file or not
    fprefix, fsuffix = os.path.splitext(fname)
    fsuffix = "." + ".".join(fname.split(".")[1::])

    if not fname.endswith((".iidm", ".xiidm", ".xml", ".xz")):
        raise HTTPException(400, "File must be .iidm/.xiidm/.xml or .xz")

    # Persist upload to a temporary file while keeping memory usage bounded
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=fsuffix) as tmp:
            tmp_path = tmp.name
            await file.seek(0)
            while True:
                chunk = await file.read(4 * 1024 * 1024)
                if not chunk:
                    break
                tmp.write(chunk)
        file_size = os.path.getsize(tmp_path)
        if file_size == 0:
            raise HTTPException(400, "Uploaded file is empty.")
        # Validate and load network off the event loop
        net = await to_thread(pn.load, tmp_path)
        if net is None:
            raise ValueError("Load returned None")
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise HTTPException(400, f"Invalid IIDM file: {e}")

    base_id = artifact_id.strip() if artifact_id else str(uuid.uuid4())
    obj_name = f"{base_id}/{file.filename}"
    meta_name = f"{base_id}/metadata.json"

    storage = _storage_client()
    if not storage.check_bucket_exists():
        storage._ensure_bucket_exists()

    # If we are reusing an artifact id, clean out old objects first to avoid duplicates
    try:
        for existing in storage.list_objects(
            storage.bucket_name, prefix=f"{base_id}/", recursive=True
        ):
            existing_key = getattr(existing, "object_name", None)
            if existing_key:
                try:
                    storage.remove_object(storage.bucket_name, existing_key)
                except Exception:
                    pass
    except Exception:
        pass

    @retry(
        stop_max_attempt_number=3,
        wait_fixed=2000,
        retry_on_exception=retry_if_storage_error,
    )
    def up_raw():
        """Upload the raw IIDM bytes to storage with retry semantics."""
        storage.upload_file(obj_name, content)

    metadata = {
        "filename": file.filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    metadata["artifact_id"] = base_id
    if description:
        metadata["description"] = description
    meta_bytes = orjson.dumps(metadata)

    @retry(
        stop_max_attempt_number=3,
        wait_fixed=2000,
        retry_on_exception=retry_if_storage_error,
    )
    def up_meta():
        """Persist the metadata JSON alongside the IIDM artifact."""
        storage.upload_file(meta_name, meta_bytes)

    try:
        with open(tmp_path, "rb") as raw_stream:
            await to_thread(
                storage.upload_file, obj_name, raw_stream, size=file_size
            )
        await to_thread(storage.upload_file, meta_name, meta_bytes)
    except StorageError as e:
        logger.error(f"Storage upload failed: {e}")
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise HTTPException(500, "Failed to upload IIDM or metadata")

    # set cookie
    response.set_cookie(
        key="iidm_file_id", value=base_id, httponly=True, samesite="lax"
    )

    # Eagerly extract and cache network data under file_id, and optionally under artifact_id
    try:
        netdata = await to_thread(extract_network_data, net)
        data_bytes = await to_thread(serialize_network_data, netdata)
        file_cache_key = f"{base_id}/network_data.json"

        @retry(
            stop_max_attempt_number=3,
            wait_fixed=2000,
            retry_on_exception=retry_if_storage_error,
        )
        def up_file_cache():
            """Store the eagerly extracted network_data cache."""
            storage.upload_file(file_cache_key, data_bytes)

        up_file_cache()
    except Exception as e:
        logger.warning(f"Failed to precompute and cache network_data: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    return {"file_id": base_id, "filename": file.filename, "artifact_id": base_id}


def _load_and_extract(file_id: str):
    """
    Shared: retrieve or extract & cache, then return network_data dict.
    """
    # ensure bucket
    storage = _storage_client()
    if not storage.check_bucket_exists():
        storage._ensure_bucket_exists()

    data_name = f"{file_id}/network_data.json"
    # try cache
    try:
        b = storage.get_file(data_name)
        return orjson.loads(b)
    except StorageNotFound:
        pass
    except StorageError as e:
        if getattr(e, "code", "") != "NoSuchKey":
            raise HTTPException(500, "Failed to retrieve cached network data")
    except Exception:
        raise HTTPException(500, "Corrupted cached network data")

    # load metadata
    meta_name = f"{file_id}/metadata.json"
    try:
        mb = storage.get_file(meta_name)
        meta = orjson.loads(mb)
        filename = meta["filename"]
    except StorageNotFound:
        raise HTTPException(404, "Metadata not found")
    except StorageError:
        raise HTTPException(500, "Failed to retrieve metadata")
    except Exception:
        raise HTTPException(500, "Corrupted metadata")

    # load raw IIDM
    obj_name = f"{file_id}/{filename}"
    try:
        content = storage.get_file(obj_name)
    except StorageNotFound:
        raise HTTPException(404, "IIDM file not found")
    except StorageError:
        raise HTTPException(500, "Failed to retrieve IIDM file")

    # extract
    try:
        netdata = extract_network_data(content)
    except ValueError as e:
        raise HTTPException(400, f"Invalid IIDM file: {e}")
    except Exception as e:
        raise HTTPException(500, f"Failed to process IIDM file: {e}")

    # serialize & cache
    try:
        data_bytes = serialize_network_data(netdata)
    except Exception as e:
        raise HTTPException(500, f"Failed to serialize network data: {e}")

    @retry(
        stop_max_attempt_number=3,
        wait_fixed=2000,
        retry_on_exception=retry_if_storage_error,
    )
    def up_cache():
        """Write freshly extracted network data back into the cache."""
        storage.upload_file(data_name, data_bytes)

    try:
        up_cache()
    except StorageError:
        logger.warning("Caching network data failed; continuing without cache")

    return netdata


@router.get("/iidm/properties/{file_id}")
async def get_iidm_properties_by_id(
    file_id: str = Path(..., description="the file_id to retrieve")
):
    """
    Retrieve properties for an IIDM file by explicit file_id.
    """
    return _load_and_extract(file_id)