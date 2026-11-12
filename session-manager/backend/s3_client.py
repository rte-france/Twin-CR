"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import os

import boto3
from botocore.config import Config

from backend.config import S3_ENDPOINT, S3_ACCESS_KEY, S3_PRIVATE_KEY

METADATA_FILE = "metadata.zip"
SIMULATOR_KEY_PREFIX = "simulators"



def make_s3_client():
    # Recent boto3 versions send extra checksums by default that some
    # S3-compatible servers reject; only send them when required.
    os.environ.setdefault("AWS_REQUEST_CHECKSUM_CALCULATION", "when_required")
    os.environ.setdefault("AWS_RESPONSE_CHECKSUM_VALIDATION", "when_required")

    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_PRIVATE_KEY,
        region_name="garage",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},  # Garage default
        ),
    )