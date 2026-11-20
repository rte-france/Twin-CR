"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from botocore.exceptions import ClientError

from backend.config import ARCHIVE_BUCKET, CACHE_DIR
from backend.s3_client import make_s3_client, SIMULATOR_KEY_PREFIX, METADATA_FILE

log = logging.getLogger("dynawo_cache")

"""
dynawo_release format:
    dynawovX.Y.Z[-<tag>]      -> scope=public, version=vX.Y.Z[-<tag>]
    dynawoRTEvX.Y.Z[-<tag>]   -> scope=RTE,    version=vX.Y.Z[-<tag>]
"""

# Semver core: no leading zeros on numeric parts. The tag is optional.
SEMVER_CORE = r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
TAG_CORE = r"(?:-([^/\\]+))?"
RELEASE_FILE_NAME = rf"dynawo(RTE)?v{SEMVER_CORE}{TAG_CORE}"
RELEASE_RE = re.compile(RELEASE_FILE_NAME)
METADATA_KEY_RE = re.compile(
    rf"{SIMULATOR_KEY_PREFIX}/(public|RTE)/v{SEMVER_CORE}{TAG_CORE}"
    r"/metadata\.zip"
)

class InvalidReleaseError(ValueError):
    """dynawo_release does not follow the naming rule."""


class ReleaseNotFoundError(LookupError):
    """The requested release does not exist in S3."""


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def get_or_retrieve(dynawo_release: str, s3) -> Path:
    """Return the local path of a release, downloading it from S3 if needed.

    Args:
        dynawo_release: release name, "dynawovX.Y.Z[-tag]" or
            "dynawoRTEvX.Y.Z[-tag]", e.g. "dynawoRTEv1.6.0-rc1".
        s3: a boto3 S3 client, e.g. boto3.client("s3", endpoint_url=...).

    Returns:
        Path to the cached file.

    Raises:
        InvalidReleaseError: dynawo_release does not follow the naming rule.
        ReleaseNotFoundError: the release does not exist in the bucket.
        botocore.exceptions.ClientError / BotoCoreError: other S3 failures.
    """
    scope, version = parse_release(dynawo_release)
    archive_name = f"{METADATA_FILE}"
    key = f"{SIMULATOR_KEY_PREFIX}/{scope}/{version}/{archive_name}"
    cache_dir = Path(CACHE_DIR)

    target = cache_dir / SIMULATOR_KEY_PREFIX / scope / version / archive_name
    ddb_folder = target.parent / "ddb"

    if ddb_folder.is_dir():
        log.debug("Cache hit: %s", target)
        return ddb_folder

    log.info("Cache miss, downloading s3://%s/%s", ARCHIVE_BUCKET, key)
    target.parent.mkdir(parents=True, exist_ok=True)
    _download(s3, key, target)
    log.info("Downloaded %s", target)
    extract_next_to_zip(target, ddb_folder)
    return ddb_folder


def parse_release(dynawo_release: str) -> tuple[str, str]:
    """Return (scope, version) from a release name.

    >>> parse_release("dynawoRTEv1.6.0-rc1")
    ('RTE', 'v1.6.0-rc1')
    >>> parse_release("dynawov1.5.0")
    ('public', 'v1.5.0')
    """
    m = RELEASE_RE.fullmatch(dynawo_release or "")
    if not m:
        raise InvalidReleaseError(
            f"Invalid dynawo_release {dynawo_release!r}. "
            "Expected dynawo[RTE]vX.Y.Z[-tag]")
    rte, major, minor, patch, tag = m.groups()
    scope = "RTE" if rte else "public"
    version = f"v{major}.{minor}.{patch}" + (f"-{tag}" if tag else "")
    return scope, version


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _download(s3, key: str, target: Path) -> None:
    """Download to "<release>.zip.part" then rename it, so an interrupted
    download never leaves a truncated file that would count as a cache hit.
    The .part name is specific to each release, so different releases can
    be downloaded at the same time."""
    tmp = target.with_name(f"{target.name}.part")
    try:
        s3.download_file(ARCHIVE_BUCKET, key, str(tmp))
        tmp.replace(target)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            raise ReleaseNotFoundError(f"s3://{ARCHIVE_BUCKET}/{key} does not exist") from e
        raise
    finally:
        tmp.unlink(missing_ok=True)


def extract_next_to_zip(zip_path: Path, extracted_dir: Path) -> None:
    staging = Path(tempfile.mkdtemp(
        dir=zip_path.parent, prefix=f".{extracted_dir.name}.staging."))
    try:
        log.info("Extracting '%s' into '%s'...", zip_path.name, extracted_dir)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(staging)
        shutil.rmtree(staging / "__MACOSX", ignore_errors=True)

        entries = list(staging.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            # Archive holds a single top-level folder: use its content
            entries[0].rename(extracted_dir)
        else:
            staging.rename(extracted_dir)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

# --------------------------------------------------------------------------
# CLI (manual testing)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import sys
    from dotenv import load_dotenv

    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Get a Dynawo release from the cache, or fetch it from S3.")
    parser.add_argument("dynawo_release",
                        help='e.g. "dynawoRTEv1.6.0-rc1" or "dynawov1.5.0"')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="[dynawo_cache] %(levelname)s: %(message)s")

    os.environ.setdefault("AWS_REQUEST_CHECKSUM_CALCULATION", "when_required")
    os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", "when_required")
    client = make_s3_client()

    try:
        print(get_or_retrieve(args.dynawo_release, client))
    except (InvalidReleaseError, ReleaseNotFoundError) as e:
        log.error("%s", e)
        sys.exit(1)