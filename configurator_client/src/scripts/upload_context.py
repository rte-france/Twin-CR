"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv
import toml
import lxml.etree as ET

from src.config import BUCKET, S3_EXPOSED_ENDPOINT

load_dotenv()

DYN_NAMESPACE = {"dyn": "http://www.rte-france.com/dynawo"}

JOB_FILE_REFERENCES = (
    (".//dyn:solver", "parFile"),
    (".//dyn:network", "iidmFile"),
    (".//dyn:network", "parFile"),
    (".//dyn:dynModels", "dydFile"),
    (".//dyn:criteria", "criteriaFile"),
    (".//dyn:curves", "inputFile"),
)

DYD_FILE_REFERENCES = (
    (".//dyn:blackBoxModel", "parFile"),
)


def upload_file(s3, local_path: Path, s3_key: str):
    print(f"Uploading {local_path} -> {s3_key}")
    s3.upload_file(str(local_path), BUCKET, s3_key)


def collect_dynawo_files(jobs_file: Path) -> set:
    """Return the Dynawo file dependencies referenced by a jobs file."""
    to_upload = set()
    working_dir = jobs_file.parent
    root = ET.parse(jobs_file).getroot()

    dyd_files = set()
    for element_path, attribute_name in JOB_FILE_REFERENCES:
        for element in root.findall(element_path, DYN_NAMESPACE):
            if attribute_name in element.attrib:
                file_path = working_dir / element.attrib[attribute_name]
                to_upload.add(file_path)
                if attribute_name == "dydFile":
                    dyd_files.add(file_path)

    for dyd_file in dyd_files:
        dyd_working_dir = dyd_file.parent
        root = ET.parse(dyd_file).getroot()
        for element_path, attribute_name in DYD_FILE_REFERENCES:
            for element in root.findall(element_path, DYN_NAMESPACE):
                if attribute_name in element.attrib:
                    to_upload.add(dyd_working_dir / element.attrib[attribute_name])

    return to_upload


def main():
    if len(sys.argv) != 3:
        print("Usage: script.py <config.toml> <context_id>")
        sys.exit(1)

    config_path = Path(sys.argv[1])
    context_id = sys.argv[2]
    base_dir = config_path.parent
    key_prefix = f"CONTEXTS/{context_id}/DATA"

    with open(config_path, "r") as f:
        config = toml.load(f)

    input_files = config.get("input_files", {})
    to_upload: set[Path] = set()

    # Collect all scalar string fields (e.g. scenario_file, job_file, ...)
    for key, value in input_files.items():
        if key in ("other_files", "other_dirs"):
            continue
        if isinstance(value, str):
            to_upload.add(base_dir / value)
        elif isinstance(value, dict):
            # Handle subsections like [input_files.scada_backend]
            for subkey, subvalue in value.items():
                if subkey in ("other_files", "other_dirs"):
                    continue
                if isinstance(subvalue, str):
                    to_upload.add(base_dir / subvalue)
            for f in value.get("other_files", []):
                to_upload.add(base_dir / f)
            for d in value.get("other_dirs", []):
                dir_path = base_dir / d
                for file in dir_path.rglob("*"):
                    if file.is_file():
                        to_upload.add(file)

    # Collect other_files list
    for f in input_files.get("other_files", []):
        to_upload.add(base_dir / f)

    # Collect other_dirs — upload all files recursively
    for d in input_files.get("other_dirs", []):
        dir_path = base_dir / d
        for file in dir_path.rglob("*"):
            if file.is_file():
                to_upload.add(file)

    # Collect the Dynawo files referenced by the jobs file (parFile, iidmFile, dydFile, ...)
    job_file = input_files.get("job_file")
    if job_file:
        to_upload |= collect_dynawo_files(base_dir / job_file)

    s3 = boto3.client("s3", region_name="garage", endpoint_url=S3_EXPOSED_ENDPOINT)

    # First clean up the prefix key space
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=BUCKET, Prefix=key_prefix)
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            s3.delete_object(Bucket=BUCKET, Key=key)

    # Upload all collected files, preserving paths relative to base_dir
    for file in to_upload:
        if not file.exists():
            raise RuntimeError(f"{file} does not exist.")
        rel_path = file.relative_to(base_dir)  # preserves structure
        upload_file(s3, file, f"{key_prefix}/{rel_path.as_posix()}")

    # Always upload the config.toml itself as "config.toml"
    upload_file(s3, config_path, f"{key_prefix}/config.toml")


if __name__ == "__main__":
    main()
