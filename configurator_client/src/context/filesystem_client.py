"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import glob
import os
import tempfile
import time
from pathlib import Path

import toml
from fastapi import HTTPException
from lxml import etree

from src.config import DSL_SERVER_URL, EXAMPLES_DIR
from src.game_master_client import GameMasterClient
from src.context.context_client import Context_Client


class Filesystem_Client(Context_Client):
    def __init__(self):
        self.base_directory = EXAMPLES_DIR

    def archive(self, clickhouse_client, context_id, simulation_id):
        pass

    def init_context_and_scenario_files(self, clickhouse_client, context_id, scenario_id, simulation_id, config_path):
        context_dir = Path(os.path.join(self.base_directory, context_id, config_path)).parent

        if not os.path.exists(context_dir):
            raise HTTPException(status_code=404, detail="Example not found")

        # Upload files to Clickhouse
        for file in glob.glob(os.path.join(context_dir, "**"), recursive=True):
            if os.path.isfile(file):
                path = os.path.relpath(file, context_dir)
                if "Titien" in file or "outputs/" in file:
                    continue
                print("Uploading", file)

                with open(file, "rb") as f:
                    data = f.read()

                clickhouse_client.insert(
                    f"{simulation_id}.InputFiles",
                    [(path, data)],
                    column_names=["input_file", "content"]
                )

    def init_game_master(self, config_file_name, context_id, scenario_id, simulation_id):
        context_dir = os.path.join(self.base_directory, context_id)
        config_path = os.path.join(context_dir, config_file_name)
        # Find iidm path from config
        config = toml.load(config_path)
        iidm_path = Path(config_path).parent / config["input_files"]["iidm_file"]
        dsl_path = config["input_files"].get("dsl_file")
        if dsl_path:
            dsl_path = Path(config_path).parent / dsl_path

        # Upload iidm
        time.sleep(10)  # Ensure game master is ready to receive files
        print()
        print(f"Uploading {iidm_path} to game master")
        game_master_client = GameMasterClient(DSL_SERVER_URL)
        game_master_artifact = "Nordic"
        reply = game_master_client.upload_iidm(Path(iidm_path), game_master_artifact)
        game_master_artifact = reply.get("artifact_id", game_master_artifact)  # Use the artifact_id from server if provided; otherwise keep the current one
        print("IIDM upload received the following reply\n", reply)

        # Upload dsl to game master and init game master
        if dsl_path:
            print(f"Uploading DSL file {dsl_path}")
            reply = game_master_client.init_simulation(Path(dsl_path), simulation_id, game_master_artifact)
        else:
            # Create a temporary empty dsl file and send it
            with tempfile.NamedTemporaryFile(mode="w", suffix=".dsl", delete=True) as tmp:
                empty_dsl_path = tmp.name
                with open(empty_dsl_path, 'w') as f:
                    f.write(
                        "set simulation duration to 999999999 seconds;\n"
                        f"set time step to {config['master']['period']} seconds;\n"
                    )

                print("Uploading empty DSL file")
                reply = game_master_client.init_simulation(Path(empty_dsl_path), simulation_id, game_master_artifact)
        print("DSL upload received the following reply\n", reply)
