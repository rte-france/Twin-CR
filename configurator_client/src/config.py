"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import os
from pathlib import Path

S3="S3"
FILE_SYSTEM="FILE_SYSTEM"

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
DSL_SERVER_HOST = os.getenv("DSL_SERVER_HOST", "localhost")
DSL_SERVER_PORT = os.getenv("DSL_SERVER_PORT", "8000")
DSL_SERVER_URL = f"http://{DSL_SERVER_HOST}:{DSL_SERVER_PORT}"
EXAMPLES_DIR = Path(__file__).parent / "../../docs/orchestrator/examples/"
NATS_URL = os.getenv("NATS_URL", "nats://localhost:4222")

STORAGE_TYPE=os.getenv("STORAGE_TYPE", S3)

BUCKET = os.getenv("BUCKET", "context-library")
S3_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "")
S3_PRIVATE_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
S3_ENDPOINT = os.getenv("AWS_ENDPOINT_URL_S3", "http://localhost:3900")
S3_EXPOSED_PORT = os.getenv("GARAGE_EXPOSED_PORT", "3900")
S3_EXPOSED_ENDPOINT = f"http://localhost:{S3_EXPOSED_PORT}"
BUCKET_ARCHIVE = os.getenv("BUCKET_ARCHIVE", "archive")
