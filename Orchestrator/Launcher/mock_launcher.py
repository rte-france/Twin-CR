"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import os
import glob
from pathlib import Path
import nats
import clickhouse_connect
import datetime
import json
import pathspec
import asyncio

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
NATS_SERVER = os.getenv("NATS_URL", "nats://localhost:4222")

EXAMPLES_DIR = Path(__file__).parent / "../../docs/orchestrator/examples/"
GITIGNORE_PATH = Path(__file__).parent / "../../gitignore"

def load_gitignore():
    if os.path.exists(GITIGNORE_PATH):
        with open(GITIGNORE_PATH) as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return pathspec.PathSpec.from_lines("gitwildmatch", [])  # empty spec


async def main():
    # Generate simulation ID
    simulation_id = "sim_" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y_%m_%d_%H_%M_%S")
    print("Simulation id:", simulation_id)

    # Pick an example (here just the first one)
    example_dir = os.path.join(EXAMPLES_DIR, "Nordic")

    # Connect to ClickHouse
    client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT
    )
    client.command(f"""
        CREATE DATABASE IF NOT EXISTS {simulation_id}""")
    client.command(f"""
        CREATE TABLE IF NOT EXISTS {simulation_id}.InputFiles (
            input_file String,
            content String
        ) ENGINE = MergeTree()
        ORDER BY (input_file)
    """)

    # gitignore = load_gitignore()
    rows = []
    for file in glob.glob(os.path.join(example_dir, "**"), recursive=True):
        if os.path.isfile(file):
            path = os.path.relpath(file, example_dir)
            # if gitignore.match_file(path):  # Skip gitignore files to avoid uploading uncessary stuff (could also skip files > 100Mb)
            #     print("Skipping", file)
            #     continue
            if "Titien" in path or "outputs/" in path or ".remi" in path:
                continue
            else:
                print("Uploading", file)

            with open(file, "rb") as f:
                data = f.read()
            rows.append((path, data))

            client.insert(
                f"{simulation_id}.InputFiles",
                [(path, data)],
                column_names=["input_file", "content"]
            )

    # Publish start command via NATS
    nc = await nats.connect(NATS_SERVER)
    init_message = {
        "simulation_id": simulation_id,
        "config_path": "config.toml"  # TODO: make parameter
        # "config_path": "docs/orchestrator/examples/Nordic/config.toml"
    }
    reply = await nc.request("Start", json.dumps(init_message).encode(), timeout=600)
    print(f"Sent init signal for {simulation_id} and got {reply.data.decode()}")

    start_message = {
        "command": "start"
    }
    reply = await nc.request("Start", json.dumps(start_message).encode(), timeout=10)
    print(f"Sent start signal for {simulation_id} and got {reply.data.decode()}")
    await nc.close()

if __name__ == "__main__":
    asyncio.run(main())
