"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from pathlib import Path
import os
import subprocess
import time
import clickhouse_connect
import requests
import toml

CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CONFIGURATOR_HOST = os.getenv("CONFIGURATOR_HOST", "localhost")
CONFIGURATOR_PORT = int(os.getenv("CONFIGURATOR_PORT", "8080"))

def wait_configurator():
    while True:
        try:
            response = requests.get(f"http://{CONFIGURATOR_HOST}:{CONFIGURATOR_PORT}/status", headers={"accept": "application/json"})
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "NOT READY":
                break

            print("Configurator not ready, received", data)

        except requests.exceptions.ConnectionError:
            print("Configurator not reachable yet")
        except requests.exceptions.Timeout:
            print("Configurator request timed out")

        time.sleep(1)

def get_simulation_id_from_configurator():
    wait_configurator()
    response = requests.get(f"http://{CONFIGURATOR_HOST}:{CONFIGURATOR_PORT}/simulation_id", headers={"accept": "application/json"})
    response.raise_for_status()
    data = response.json()
    return data.get("simulation_id")

def get_config_path_from_configurator():
    wait_configurator()
    response = requests.get(f"http://{CONFIGURATOR_HOST}:{CONFIGURATOR_PORT}/config_path", headers={"accept": "application/json"})
    response.raise_for_status()
    data = response.json()
    return data.get("config_path")

def fetch_input_files_from_simulation_id(simulation_id: str) -> Path:
    client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT
    )
    # Fetch list of files
    result = client.query(f"SELECT input_file FROM `{simulation_id}`.InputFiles")
    files = [row[0] for row in result.result_rows]

    out_dir = f"/tmp/{simulation_id}"
    # Fetch all files individually
    for relative_path in files:
        file_result = client.query(
            "SELECT content FROM `{db}`.InputFiles WHERE input_file = {path}".format(
                db=simulation_id, path=f"'{relative_path}'"
            )
        )
        content: bytes = file_result.result_rows[0][0]

        destination = os.path.join(out_dir, relative_path)
        os.makedirs(os.path.dirname(destination), exist_ok=True)

        print(f"Downloading {relative_path} from ClickHouse and writing to {destination}")
        with open(destination, "wb") as f:
            f.write(content if isinstance(content, bytes) else content.encode())
    return Path(out_dir)

MODE = os.getenv("MODE", "FILESYSTEM")
print("MODE:", MODE)


def launch_automata():
    """
    Launch the automata commands listed in the 'automata_commands' field of the input TOML config
    """
    if MODE == "FILESYSTEM":
        config_path = os.getenv("CONFIG_PATH", "The CONFIG_PATH env variable must be set when using FILESYSTEM mode")
    else:  # CLICKHOUSE
        simulation_id = get_simulation_id_from_configurator()
        working_dir = fetch_input_files_from_simulation_id(simulation_id)
        config_path = working_dir / get_config_path_from_configurator()

    with open(config_path, "r") as f:
        config = toml.load(f)

    # Extract commands
    commands = config.get("automata_commands", [])
    if not isinstance(commands, list):
        raise ValueError("'automata_commands' must be a list in the TOML file.")
    if len(commands) == 0:
        print("No commands to run")
        return

    # Change to directory of TOML file
    toml_dir = os.path.dirname(config_path)
    os.chdir(toml_dir)

    # Prepare logs directory
    logs_dir = os.path.join(Path(__file__).parent, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    print(f"Logs will be saved in: {logs_dir}")

    # Launch all commands in parallel with separate logs
    processes = []
    for i, cmd in enumerate(commands):
        if not isinstance(cmd, str):
            print(f"Skipping invalid command (not a string): {cmd}")
            continue

        log_file = os.path.join(logs_dir, f"automaton_{i}.log")
        log_handle = open(log_file, "w")
        log_handle.write(f"Logs of command {cmd}\n")
        log_handle.flush()
        proc = subprocess.Popen(cmd, shell=True, stdout=log_handle, stderr=log_handle)
        processes.append((cmd, proc, log_handle))

    # Wait for all processes to complete
    for cmd, proc, log_handle in processes:
        proc.wait()
        log_handle.close()
        print(f"Command {cmd} exited with status {proc.returncode}")


if __name__ == "__main__":
    launch_automata()
