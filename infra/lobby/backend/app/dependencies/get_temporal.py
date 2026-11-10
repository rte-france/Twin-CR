"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from fastapi import HTTPException, Request
from temporalio.client import Client


async def get_temporal_client(request: Request) -> Client:
    client = getattr(request.app.state, "temporal_client", None)
    if client is None:
        raise HTTPException(status_code=500, detail="Temporal Client not connected")
    return client
