"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import asyncio
import datetime
import json
import logging
from contextlib import asynccontextmanager
import os
from pathlib import Path

import clickhouse_connect
import nats.aio.msg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.ServerState import ServerState
from src.config import CLICKHOUSE_HOST, CLICKHOUSE_PORT, NATS_URL, STORAGE_TYPE, S3
from src.context.filesystem_client import Filesystem_Client
from src.context.s3_client import S3_Client

load_dotenv()
WITH_LEGACY_DSL = os.getenv("WITH_LEGACY_DSL", "false").lower() in ("1", "true", "yes")

logger = logging.getLogger("uvicorn.error")

GLOBAL_TIMEOUT = 300.0

@asynccontextmanager
async def lifespan(app: FastAPI):
    # During startup, initialize nats socket
    nats_client = await nats.connect(NATS_URL)
    await nats_client.subscribe("stop", cb=stop_message_handler)
    logger.info("nats handshake ok")

    app.state.state = ServerState()
    app.state.state.nats_client = nats_client
    yield
    # During shutdown, first release nats socket
    nats_client.close()

app = FastAPI(
    title="Configurator client API",
    description="Configurator client API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(
            call_next(request),
            timeout=GLOBAL_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return JSONResponse(
            status_code=504,
            content={"detail": f"Request timeout after {GLOBAL_TIMEOUT}"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Starlette's default is a bare "Internal Server Error" body, which the
    # session-manager relays as-is; give it the actual reason instead.
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}"},
    )


context_client = None
if STORAGE_TYPE == S3:
    logger.info("Using S3 client")
    context_client = S3_Client()
else:
    logger.info("Using filesystem client")
    context_client = Filesystem_Client()



@app.get("/init/{context_id}")
async def init(
        context_id: str,
        scenario_id: str = Query(default=None),
        config_path: str = Query(default="config.toml"),
):
    state: ServerState = app.state.state

    if state.status != "NOT READY":
        raise HTTPException(status_code=409, detail="A simulation is already active")

    # Generate simulation ID
    simulation_id = "sim_" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y_%m_%d_%H_%M_%S")
    print("Simulation id:", simulation_id)

    # ClickHouse and the context download are synchronous. On the event loop
    # they blocked it outright, which is why the timeout middleware could never
    # fire: wait_for only gets control at an await.
    def prepare_clickhouse():
        clickhouse_client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT
        )
        clickhouse_client.command(f"""
            CREATE DATABASE IF NOT EXISTS {simulation_id}""")
        clickhouse_client.command(f"""
            CREATE TABLE IF NOT EXISTS {simulation_id}.InputFiles (
                input_file String,
                content String
            ) ENGINE = MergeTree()
            ORDER BY (input_file)
        """)
        context_client.init_context_and_scenario_files(
            clickhouse_client, context_id, scenario_id, simulation_id, config_path
        )
        context_client.init_dynawo_file(
            clickhouse_client, context_id, scenario_id, simulation_id, config_path
        )

    await asyncio.to_thread(prepare_clickhouse)

    # Send init command to orchestrator
    init_message = {
        "simulation_id": simulation_id,
        "config_path": config_path,
        "context_id": context_id
    }
    reply = await state.nats_client.request("Start", json.dumps(init_message).encode(), timeout=60)

    try:
        payload = json.loads(reply.data.decode())
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="Orchestrator returned invalid JSON",
        )

    if payload.get("status") != "READY":
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Orchestrator init failed",
                "orchestrator_reply": payload,
            },
        )

    # Init game master
    if WITH_LEGACY_DSL:
        await asyncio.to_thread(
            context_client.init_game_master, config_path, context_id, scenario_id, simulation_id
        )

    state.status = "READY"
    state.current_simulation_id = simulation_id
    state.config_path = config_path
    state.context_id = context_id
    state.scenario_id = scenario_id

    return {
        "simulation_id": simulation_id,
        "orchestrator_reply": payload,
    }


@app.get("/start")
async def start():
    state: ServerState = app.state.state
    if state.status != "READY":
        raise HTTPException(status_code=409, detail="Configurator is not READY")

    start_message = {
        "command": "start"
    }
    reply = await state.nats_client.request("Start", json.dumps(start_message).encode(), timeout=10)
    payload = json.loads(reply.data.decode())

    if payload.get("status") == "OK":
        state.status = "STARTED"

    return payload


@app.get("/simulation_id")
def get_simulation_id():
    state: ServerState = app.state.state
    if state.current_simulation_id is None:
        raise HTTPException(status_code=404, detail="No active simulation")
    return {"simulation_id": state.current_simulation_id}

@app.get("/config_path")
def get_config_path():
    state: ServerState = app.state.state
    if state.config_path is None:
        raise HTTPException(status_code=404, detail="No active simulation")
    return {"config_path": Path(state.config_path).name}


@app.get("/status")
def get_status():
    state: ServerState = app.state.state
    return {"status": state.status}


@app.get("/archive")
def get_archive(
        context_id: str,
        simulation_id: str
    ):
    clickhouse_client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT
    )

    context_client.archive(clickhouse_client, context_id, simulation_id)


async def stop_message_handler(msg: nats.aio.msg.Msg):
    print("Received stop signal", msg.data.decode())
    state: ServerState = app.state.state
    state.status = "STOPPED"
    # Connect to ClickHouse
    clickhouse_client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT
    )
    context_client.archive(clickhouse_client, state.context_id, state.current_simulation_id)
    # TODO: drop db
    state.reset()
