"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import csv
import json
import os
import subprocess
import tarfile
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import clickhouse_connect
import toml
import lxml.etree as ET

load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))

DYN_NAMESPACE = {"dyn": "http://www.rte-france.com/dynawo"}

JOB_FILE_REFERENCES = (
    (".//dyn:solver", "parFile"),
    (".//dyn:network", "iidmFile"),
    (".//dyn:network", "parFile"),
    (".//dyn:dynModels", "dydFile"),
    (".//dyn:criteria", "criteriaFile"),
    (".//dyn:curves", "inputFile"),
)

DYD_FILE_REFERENCES = (
    (".//dyn:blackBoxModel", "parFile"),
)


def parse_args():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("sim_name", type=str, help="sim_name, key to clickhouse tables")
    return parser.parse_args()


def post_clickhouse_query(query):
    client = clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST, port=CLICKHOUSE_PORT
    )
    return client.query(query).result_rows


def fetch_commands(sim_name, output_dir):
    query = f"""
    SELECT 
        command,
        zmq_flag,
        event_count, 
        time
    FROM "{sim_name}"."RawDynawoCommand"
    ORDER BY event_count
    """

    raw_commands = post_clickhouse_query(query)
    output_file = os.path.join(output_dir, "commands.csv")
    
    with open(output_file, "w", newline="") as output:
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["time", "command", "zmq_flag", "event_count"])
        for row in raw_commands:
            command_str, zmq_flag, event_count, time = row
            writer.writerow([time, command_str, zmq_flag, event_count])

    print(f"[INFO] wrote {len(raw_commands)} commands to {output_file}")


def fetch_file(sim_name, file_name, output_dir):
    output_file = os.path.join(output_dir, file_name)
    print(output_file)
    try:
        query = f"""
        SELECT
            content
        FROM "{sim_name}"."InputFiles"
        WHERE input_file = '{file_name}'
        """

        rows = post_clickhouse_query(query)
        if not rows:
             raise RuntimeError(f"File {file_name} not found in database")

        content = rows[0][0]

        with open(output_file, "w") as output:
            output.write(content)

    except Exception as e:
        raise RuntimeError(f"[ERROR] Failed to fetch {file_name}: {e}")

    return output_file


def fetch_dynawo_files(sim_name, input_jobs_file, output_dir):
    """Fetch files from ClickHouse, adding Dynawo file dependencies as they are discovered."""
    fetched_files = set()

    jobs_file = fetch_file(sim_name, input_jobs_file, output_dir)
    root = ET.parse(jobs_file).getroot()

    dyd_files = set()
    for element_path, attribute_name in JOB_FILE_REFERENCES:
        for element in root.findall(element_path, DYN_NAMESPACE):
            if attribute_name in element.attrib:
                filename = element.attrib[attribute_name]
                if filename in fetched_files:
                    continue
                file_path = fetch_file(sim_name, filename, output_dir)
                fetched_files.add(filename)
                if attribute_name == "dydFile":
                    dyd_files.add(file_path)

    for dyd_file in dyd_files:
        root = ET.parse(dyd_file).getroot()
        for element_path, attribute_name in DYD_FILE_REFERENCES:
            for element in root.findall(element_path, DYN_NAMESPACE):
                if attribute_name in element.attrib:
                    filename = element.attrib[attribute_name]
                    if filename in fetched_files:
                        continue
                    fetch_file(sim_name, filename, output_dir)
                    fetched_files.add(filename)


def add_file_if_needed(file_name, fetched_files, files_to_fetch):
    if file_name and file_name not in fetched_files:
        files_to_fetch.add(file_name)


def load_config(config_file):
    with open(config_file, "r") as config:
        return toml.load(config)


def write_docker_logs(output_dir):
    output_file = os.path.join(output_dir, "DockerLogs")
    container = "twincr-core"
    result = subprocess.run(
        ["docker", "logs", "--tail", "100", container],
        capture_output=True,
        text=True
    )

    logs = result.stdout + result.stderr

    with open(output_file, "w") as f:
        f.write(logs)


def main(sim_name):
    archive_name = sim_name + ".tar.xz"

    with tempfile.TemporaryDirectory() as output_dir:
        fetch_commands(sim_name, output_dir)

        config_file = fetch_file(sim_name, "config.toml", output_dir)

        config_data = load_config(config_file)
        input_jobs_file = config_data.get("input_files", {}).get("job_file")
        if input_jobs_file is None:
            raise RuntimeError(f"[ERROR] 'job_file' not found in {config_file}")
        fetch_dynawo_files(sim_name, input_jobs_file, output_dir)

        write_docker_logs(output_dir)
        make_archive(output_dir, archive_name, sim_name)


def make_archive(output_dir, archive_name, sim_name):
    with tarfile.open(archive_name, "w:xz") as tar:
        tar.add(output_dir, arcname=sim_name)
    print(f"[INFO] Created archive {archive_name}")


if __name__ == "__main__":
    args = parse_args()
    main(args.sim_name)
