"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from contextlib import asynccontextmanager

import aioboto3
from aiobotocore.config import AioConfig
from fastapi import Depends

from app.dependencies.get_config import Settings, get_settings

S3_REGION = "us-east-1"
_SESSION = aioboto3.Session()


async def get_s3_client(settings: Settings = Depends(get_settings)):
    async with _SESSION.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=S3_REGION,
        config=AioConfig(
            s3={"addressing_style": "path"},
            signature_version="s3v4",
            connect_timeout=10,
            read_timeout=300,
            retries={"max_attempts": 3},
        ),
    ) as client:
        yield client
