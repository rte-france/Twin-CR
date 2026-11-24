"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""
from __future__ import annotations

#!/usr/bin/env python3
"""
publish_dynawo.py

Takes a Dynawo release zip, validates and cleans it, separates the ddb
metadata files, then uploads two archives to an S3 bucket (e.g. Garage):

    s3://archive/simulators/<scope>/<version>/metadata.zip
    s3://archive/simulators/<scope>/<version>/dynawo.zip

Accepted zip names:
    dynawovX.Y.Z[-<tag>].zip      -> scope=public, version=vX.Y.Z[-<tag>]
    dynawoRTEvX.Y.Z[-<tag>].zip   -> scope=RTE,    version=vX.Y.Z[-<tag>]
    (the -<tag> suffix is optional and can be any string)

Usage:
    publish_dynawo.py <archive.zip> [--endpoint URL] [--region R] [--bucket B]

"""

import argparse
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

from backend.s3_client import make_s3_client, METADATA_FILE
from backend.simulator.simulator_cache_handler import parse_release, extract_next_to_zip

load_dotenv()

log = logging.getLogger("publish_dynawo")

METADATA_SUFFIXES = (".xml", ".extvar")


class PublishError(Exception):
    """Expected, user-facing failure."""


# --------------------------------------------------------------------------
# Zip helpers
# --------------------------------------------------------------------------
def zip_dir(src: Path, out: Path) -> None:
    """Zip the *content* of src into out (no top-level folder)."""
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            zf.write(path, path.relative_to(src))


# --------------------------------------------------------------------------
# Processing steps
# --------------------------------------------------------------------------
def remove_example(extracted_dir: Path) -> None:
    example = extracted_dir / "examples"
    if example.is_dir():
        shutil.rmtree(example)
        log.info("Deleted 'examples' folder")
    else:
        log.warning("No 'examples' folder found, nothing to delete")


def check_layout(extracted_dir: Path) -> None:
    if not (extracted_dir / "dynawo.sh").is_file():
        raise PublishError("'dynawo.sh' not found at root of extracted folder")
    log.info("Found dynawo.sh")

    for name in ("bin", "lib"):
        if not (extracted_dir / name).is_dir():
            raise PublishError(f"'{name}' folder not found at root of extracted folder")
        log.info("Found '%s' folder", name)


def move_metadata(extracted_dir: Path, metadata_dir: Path) -> int:
    """Move ddb/**/*.xml and *.extvar to metadata_dir, keeping subfolders."""
    ddb = extracted_dir / "ddb"
    if not ddb.is_dir():
        raise PublishError("'ddb' folder not found at root of extracted folder")

    metadata_dir.mkdir()
    count = 0
    for root, _dirs, files in os.walk(ddb):
        for name in files:
            if not name.endswith(METADATA_SUFFIXES):
                continue
            src = Path(root) / name
            dst = metadata_dir / src.relative_to(ddb)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            count += 1

    if count == 0:
        raise PublishError("No .xml or .extvar files found in 'ddb'")
    log.info("Moved %d metadata file(s) to '%s'", count, metadata_dir)
    return count


# --------------------------------------------------------------------------
# S3
# --------------------------------------------------------------------------


def upload(s3, file: Path, bucket: str, key: str) -> None:
    log.info("Uploading %s -> s3://%s/%s", file.name, bucket, key)
    s3.upload_file(str(file), bucket, key,
                   ExtraArgs={"ContentType": "application/zip"})


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def run(zip_path: Path, endpoint: str, region: str, bucket: str) -> None:
    if not zip_path.is_file():
        raise PublishError(f"File not found: {zip_path}")
    if not zipfile.is_zipfile(zip_path):
        raise PublishError(f"Not a valid zip archive: {zip_path}")

    scope, version = parse_release(zip_path.stem)
    log.info("scope=%s", scope)
    log.info("version=%s", version)

    metadata_key = f"simulators/{scope}/{version}/{METADATA_FILE}"
    dynawo_key = f"simulators/{scope}/{version}/{zip_path.name}"

    # Fail fast on bad credentials / missing bucket, before touching files
    s3 = make_s3_client()
    s3.head_bucket(Bucket=bucket)

    zip_path = zip_path.resolve()
    extracted_dir = zip_path.parent / zip_path.name.removesuffix(".zip")
    metadata_dir = extracted_dir.with_name(f"{extracted_dir.name}-metadata")

    for path in (extracted_dir, metadata_dir):
        if path.exists():
            raise PublishError(f"Target already exists: {path}")

    success = False
    try:
        extract_next_to_zip(zip_path, extracted_dir)
        remove_example(extracted_dir)
        check_layout(extracted_dir)
        move_metadata(extracted_dir, metadata_dir)

        with tempfile.TemporaryDirectory(prefix=f"{extracted_dir.name}.upload.") as tmp:
            metadata_zip = Path(tmp) / "metadata.zip"
            dynawo_zip = Path(tmp) / "dynawo.zip"

            log.info("Creating metadata.zip...")
            zip_dir(metadata_dir, metadata_zip)
            log.info("Creating dynawo.zip...")
            zip_dir(extracted_dir, dynawo_zip)

            upload(s3, metadata_zip, bucket, metadata_key)
            upload(s3, dynawo_zip, bucket, dynawo_key)

        success = True
    finally:
        if not success:
            # Remove what this run created so it can be re-run cleanly
            log.warning("Failed, cleaning up created folders")
            shutil.rmtree(extracted_dir, ignore_errors=True)
            shutil.rmtree(metadata_dir, ignore_errors=True)

    log.info("  Extracted folder: %s", extracted_dir)
    log.info("  Metadata folder:  %s", metadata_dir)
    log.info("  Uploaded:         s3://%s/%s", bucket, metadata_key)
    log.info("  Uploaded:         s3://%s/%s", bucket, dynawo_key)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Dynawo release zip and upload it to S3.")
    parser.add_argument("zip_file", type=Path,
                        help="dynawo[RTE]vX.Y.Z[-tag].zip")
    parser.add_argument("--endpoint",
                        default=os.environ.get("GARAGE_ENDPOINT", "http://localhost:3900"),
                        help="S3 endpoint URL (default: %(default)s)")
    parser.add_argument("--region",
                        default=os.environ.get("GARAGE_REGION", "garage"),
                        help="S3 region (default: %(default)s)")
    parser.add_argument("--bucket",
                        default=os.environ.get("S3_BUCKET", "archive"),
                        help="Target bucket (default: %(default)s)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="[publish_dynawo] %(levelname)s: %(message)s")

    try:
        run(args.zip_file, args.endpoint, args.region, args.bucket)
    except PublishError as e:
        log.error("%s", e)
        return 1
    except (ClientError, BotoCoreError) as e:
        log.error("S3 error: %s", e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
