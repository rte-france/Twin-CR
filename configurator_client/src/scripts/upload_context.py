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


def directory_files(dir_path: Path, required: bool = True) -> set:
    if required and not dir_path.is_dir():
        raise RuntimeError(f"{dir_path} is not a directory.")
    return {file for file in dir_path.rglob("*") if file.is_file()}


def collect_input_files(section: dict, base_dir: Path) -> set:
    """Files of an [input_files] (sub)section: *_dir keys and other_dirs are directories, the other paths are files."""
    to_upload = set()
    for key, value in section.items():
        if key == "other_files":
            to_upload |= {base_dir / f for f in value}
        elif key == "other_dirs":
            for d in value:
                to_upload |= directory_files(base_dir / d, required=False)
        elif isinstance(value, str):
            to_upload |= directory_files(base_dir / value) if key.endswith("_dir") else {base_dir / value}
        elif isinstance(value, dict):
            to_upload |= collect_input_files(value, base_dir)
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

    # Every path of [input_files] and its subsections (e.g. [input_files.scada_backend]):
    # *_dir keys and other_dirs are directories (uploaded recursively), the other strings and other_files are files
    to_upload: set[Path] = collect_input_files(input_files, base_dir)

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
