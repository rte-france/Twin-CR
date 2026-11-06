"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path

import clickhouse_connect
from dotenv import dotenv_values, load_dotenv
import pandas as pd
import pytest
import requests
from nats.aio.client import Client as NATS

load_dotenv(Path(__file__).parent.parent / ".env-tests", override=True)
COMPOSE_FILE = Path(__file__).parent.parent / "docker-compose.yaml"
OVERRIDE_FILE = Path(__file__).parent.parent / "docker-compose-tests.overrides.yaml"
NATS_PORT = os.getenv("NATS_EXPOSED_PORT", "4222")
NATS_URL = f"nats://localhost:{NATS_PORT}"
CLICKHOUSE_HOST = "localhost"
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_EXPOSED_PORT", "8123"))
CONFIGURATOR_HOST = "localhost"
CONFIGURATOR_PORT = int(os.getenv("CONFIGURATOR_EXPOSED_PORT", "8080"))
CONFIGURATOR_URL = f"http://{CONFIGURATOR_HOST}:{CONFIGURATOR_PORT}"
FILE_UPLOADER_UV_ROOT = (Path(__file__).parent.parent / "configurator_client").resolve()

def docker_compose(*args):
    """
    Run docker compose command with list of args
    """
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "-f", OVERRIDE_FILE] + list(args)
    try:
        subprocess.run(cmd)
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise e

def docker_compose_file(compose_file, *args):
    """
    Run docker compose command with a given compose file and list of args
    """
    cmd = ["docker", "compose", "-f", compose_file] + list(args)
    try:
        subprocess.run(cmd)
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise e


def docker_compose_redirect_output(*args) -> str:
    """
    Run docker compose command with list of args and returns the standard output of the process
    """
    cmd = ["docker", "compose", "-f", COMPOSE_FILE, "-f", OVERRIDE_FILE] + list(args)
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(e.output)
        raise e


def prune_anonymous_volumes() -> None:
    """Reap the per-run anonymous volumes, leaving every named volume alone."""
    subprocess.run(
        ["docker", "volume", "prune", "-f",
         "--filter", "label=com.docker.volume.anonymous"],
        check=True, stdout=subprocess.DEVNULL,
    )


@pytest.fixture(scope="function")
def compose_environment(request):
    """
    Bring the docker-compose stack up before each test, and down after.
    (This also kills any remaining processes, so simulations do not have to be explicitly killed if they hang.)
    """
    scenario = request.param
    docker_compose("up", "-d")
    wait_for_health()

    yield scenario  # run the test

    docker_compose("logs")

    # Not "down -v": that would take the session-manager's database, which these tests never touch.
    docker_compose("down")

    # Prune anonymous volumes (from Clickhouse) to avoid accumulating disk space
    prune_anonymous_volumes()

# Disabled as garage is now in the main compose (although it probably shouldn't be)
# @pytest.fixture(scope="session", autouse=True)
# def garage_compose():
#     """
#     Always keep the garage compose up during all tests (scope session)
#     """
#     garage_file = Path(__file__).parent.parent / "configurator_server/docker-compose-garage.yaml"
#     docker_compose_file(garage_file, "up", "-d")
#     time.sleep(5)
#
#     yield
#
#     docker_compose_file(garage_file, "down")


def wait_for_health(timeout=60):
    """
    Wait until docker services report healthy.
    """
    start = time.time()
    while True:
        ps_json = docker_compose_redirect_output("ps", "--format", "json")
        # ps actually returns a list as Newline-Delimited JSON, so load accordingly
        services = [json.loads(line) for line in ps_json.splitlines() if line.strip().startswith("{")]

        required_services = {"twincr-core", "clickhouse", "configurator-client"}
        required_services_status = {name: False for name in required_services}

        for service in services:
            name = service.get("Name")
            if name in required_services_status and service.get("Health") == "healthy":
                required_services_status[name] = True

        if all(required_services_status.values()):
            return

        if time.time() - start > timeout:
            subprocess.run(["docker", "compose", "logs", "--tail=50"], check=False)
            raise RuntimeError(f"Not all services healthy after {timeout}s: {required_services_status}")

        time.sleep(1)


async def start_simulation(scenario_name: str, config_path: str, scenario_id: str) -> str:
    # Generate the game_master_outputs.json and other mapping files if needed
    config_preparator_path = Path(config_path).parent / "cfg.sh"
    if config_preparator_path.exists():
        subprocess.run(["./cfg.sh"],
                       cwd=str(Path(config_path).parent),  # Run script from its own directory
                       check=True)  # Raise if script fails


    env = os.environ.copy()
    env.update(dotenv_values(FILE_UPLOADER_UV_ROOT / ".env"))
    subprocess.run(
        ["uv", "run", "upload_context", str(Path(config_path).resolve()), scenario_name],
        cwd=FILE_UPLOADER_UV_ROOT,
        check=True,
        env=env
    )

    # Init simulation
    response = requests.get(
        f"{CONFIGURATOR_URL}/init/{scenario_name}",
        params={
            # "config_path" always set to config.toml in CLICKHOUSE mode
            "scenario_id": scenario_id
        },
        headers={"accept": "application/json"}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise requests.exceptions.HTTPError(
            f"{e} - response body: {response.text}", response=response
        ) from e
    data = response.json()
    simulation_id = data["simulation_id"]

    # Start simulation
    response = requests.get(
        f"{CONFIGURATOR_URL}/start",
        headers={"accept": "application/json"}
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        raise requests.exceptions.HTTPError(
            f"{e} - response body: {response.text}", response=response
        ) from e

    return simulation_id

async def wait_for_simulation(timeout):
    """
    Wait until the Orchestrator sends the stop signal
    """
    nc = NATS()
    await nc.connect(NATS_URL)

    future = asyncio.get_event_loop().create_future()
    async def handler(msg):
        print(f"Received stop signal: {msg}")
        future.set_result(True)

    sub = await nc.subscribe("stop", cb=handler)

    try:
        await asyncio.wait_for(future, timeout)
    except asyncio.TimeoutError:
        print("Simulation timeout")  # Don't raise error as it might be expected (some simulations never finish, and Nordic hangs at the end)

    await sub.unsubscribe()
    await nc.close()


def fetch_results(sim_id: str, start_time: float, stop_time: float, variable_list = []) -> pd.DataFrame:
    """
    Fetch the ClickHouse time series results.
    """
    client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT
    )

    query = f"""
        SELECT id, value, time_sent, time_received
        FROM {sim_id}.MeasurementReceived
        WHERE time_received>={start_time}
            AND time_received<={stop_time}
        """
    if variable_list:
        variable_list_sql = ", ".join(f"'{t}'" for t in variable_list)
        query += f" AND id IN ({variable_list_sql})"

    df = pd.DataFrame(client.query(query).result_rows, columns=["id", "value", "time_sent", "time_received"])

    # Sort by time_received and id for consistent comparison
    df = df.sort_values(
        by = ["time_received", "id"],
        ascending = [True, True],
        ignore_index = True
    )
    return df


SCENARIOS = [
    {
        "scenario_name": "Nordic_nrt",
        "config_path": "docs/orchestrator/examples/Nordic/config.toml",
        "scenario_id": "Nordic.dsl",
        "start_time": 0,
        "stop_time": 200,
        "timeout": 500,  # Cannot run in x5 speed on github (2vCPU machine), actually, sometimes even too slow
        "variables": ["NETWORK_L4032-4044_breaker1_state_value", "NETWORK_L4032-4044_breaker2_state_value", "NETWORK_4047_401_U_value",
            "NETWORK_L4011-4012_iS1ToS2Side1_value",
            "NETWORK_L4011-4012_iS2ToS1Side2_value",
            "NETWORK_L4011-4021_iS1ToS2Side1_value",
            "NETWORK_L4011-4021_iS2ToS1Side2_value",
            "NETWORK_L4011-4022_iS1ToS2Side1_value",
            "NETWORK_L4011-4022_iS2ToS1Side2_value",
            "NETWORK_L4011-4071_iS1ToS2Side1_value",
            "NETWORK_L4011-4071_iS2ToS1Side2_value",
            "NETWORK_L4012-4022_iS1ToS2Side1_value",
            "NETWORK_L4012-4022_iS2ToS1Side2_value",
            "NETWORK_L4012-4071_iS1ToS2Side1_value",
            "NETWORK_L4012-4071_iS2ToS1Side2_value",
            "NETWORK_L4021-4032_iS1ToS2Side1_value",
            "NETWORK_L4021-4032_iS2ToS1Side2_value",
            "NETWORK_L4021-4042_iS1ToS2Side1_value",
            "NETWORK_L4021-4042_iS2ToS1Side2_value"
        ]
    }
]

@pytest.mark.asyncio
@pytest.mark.parametrize("compose_environment", SCENARIOS, indirect=["compose_environment"])
async def test_simulation_scenario(compose_environment):
    """
    Run all tests
    compose_environment is a "fixture", so it is run before and after each test to prepare it
    """
    scenario = compose_environment  # This pass the scenario back from the fixture to here (from the yield in compose_environment)
    print(f"Running scenario {scenario}")
    scenario_name = scenario["scenario_name"]
    config_path = scenario["config_path"]
    scenario_id = scenario["scenario_id"]

    print("Starting simulation: ", scenario_name, config_path, scenario_id)
    simulation_id = await start_simulation(scenario_name, config_path, scenario_id)
    await wait_for_simulation(timeout = scenario["timeout"])
    print("Simulation ended")
    time.sleep(10)  # Ensure Clickhouse logs are published
    df = fetch_results(simulation_id, scenario["start_time"], scenario["stop_time"], scenario.get("variables", []))

    reference_dir = Path(__file__).parent / "reference"
    reference_dir.mkdir(exist_ok=True)
    reference_path = reference_dir / f"{scenario_name}.csv"

    if not reference_path.exists():
        # First run: save output as reference
        df.to_csv(reference_path, index=False)
        pytest.skip(f"First run of scenario saved to {reference_path}. Re-run test.")
        return

    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    df.to_csv(results_dir / f"{scenario_name}.csv", index=False)

    expected = pd.read_csv(reference_path)
    # Compare to reference
    try:
        pd.testing.assert_frame_equal(
            df.reset_index(drop=True),
            expected.reset_index(drop=True),
            check_exact=False,
            rtol=1e-4,
        )
    except AssertionError as e:
        # Print dataframe if different from reference
        print("Result dataframe")
        print(df.to_csv(index=False))
        raise
