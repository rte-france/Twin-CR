"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import traceback
from contextlib import asynccontextmanager

import temporalio.exceptions
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from temporalio.client import Client

from app.api.v1 import execution, files, lobby, nomad, projects, file
from app.dependencies.get_config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    try:
        app.state.temporal_client = await Client.connect(
            settings.temporal_address, namespace=settings.temporal_namespace
        )
    except (RuntimeError, temporalio.exceptions.TemporalError) as e:
        print(f"Failed to connect to Temporal: {e}")
        app.state.temporal_client = None
    yield


app = FastAPI(
    title="TwinEu Lobby API",
    description="API for managing the lifecycle of TwinEu sessions.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):
    print(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )


for router in (
    lobby.router,
    execution.router,
    files.files_router,
    file.router,
    files.directories_router,
    nomad.router,
    projects.router,
):
    app.include_router(router)
