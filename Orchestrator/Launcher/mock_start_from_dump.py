"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import nats
import json
import asyncio

CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_PORT = 8123
NATS_SERVER = "nats://localhost:4222"

async def main():
    # Publish start command via NATS
    nc = await nats.connect(NATS_SERVER)
    simulation_id = "sim_2025_11_05_15_48_00"
    init_message = {
        "simulation_id": simulation_id,
        "config_path": "Orchestrator/config/Nordic/config.toml",  # TODO: make parameter
        # "config_path": "docs/orchestrator/examples/Nordic/config.toml"
        "start_time": 100,
    }
    reply = await nc.request("Start", json.dumps(init_message).encode(), timeout=30)
    print(f"Sent init signal for {simulation_id} and got {reply.data.decode()}")

    start_message = {"command": "start"}
    reply = await nc.request("Start", json.dumps(start_message).encode(), timeout=10)
    print(f"Sent start signal for {simulation_id} and got {reply.data.decode()}")
    await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
