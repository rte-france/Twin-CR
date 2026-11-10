"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client

from app.dependencies.auth import get_current_user
from app.dependencies.get_config import Settings, get_settings
from app.dependencies.get_db import get_db
from app.dependencies.get_s3 import get_s3_client
from app.dependencies.get_temporal import get_temporal_client
from app.schemas import CurrentUser

DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
TemporalClientDep = Annotated[Client, Depends(get_temporal_client)]
S3ClientDep = Annotated[Any, Depends(get_s3_client)]
