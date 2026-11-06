"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import tarfile
import time

import zmq
import csv
import argparse
import os
import toml
import subprocess

DYNAWO_SCRIPT = os.environ.get("DYNAWO_SCRIPT")

def load_commands_from_csv(path):
    commands = []
    with open(path, "r") as f:
        reader = csv.DictReader(f, delimiter=";")
        for item in reader:
            commands.append(
                Command(
                    item["command"],
                    item["zmq_flag"]
                )
            )

    return commands
# =====================
# ControlSender (REQ)
# =====================
class ControlSender:
    def __init__(self, address="tcp://localhost:5555"):
        self.address = address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.address)

    def close(self):
        self.socket.close()
        self.context.term()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def send(self, command, zmq_flag):
        print(f"Sending {command} (flag: {zmq_flag})")
        try:
            self.socket.send_string(command, zmq_flag)
            if zmq_flag == 0:
                if self.socket.poll(60000, zmq.POLLIN):
                    ack = self.socket.recv()  # ack
                    print(f"Received ack: {ack}")
                else:
                    print("Timeout waiting for trigger ack")
                    # Reset socket state by recreating it
                    self.socket.close()
                    self.socket = self.context.socket(zmq.REQ)
                    self.socket.connect(self.address)
        except zmq.ZMQError as e:
            print(f"ZMQ Error during send_trigger: {e}")
            # Reset socket state
            self.socket.close()
            self.socket = self.context.socket(zmq.REQ)
            self.socket.connect(self.address)

# =====================
# Receiver (SUB)
# =====================
class Receiver:
    def __init__(self, address="tcp://localhost:5556"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.connect(address)
        self.socket.setsockopt(zmq.SUBSCRIBE, b"constraints")
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def close(self):
        self.socket.close()
        self.context.term()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def wait_for_constraints(self, timeout=100):
        events = dict(self.poller.poll(timeout))
        if self.socket in events:
            recv_topic = self.socket.recv_string()
            if recv_topic == "constraints":
                return True
        return False


class Command:
    def __init__(self, command, zmq_flag):
        self.command = command
        self.zmq_flag = int(zmq_flag)
        self.sent = False


def load_config(config_file):
    with open(config_file, "r") as config:
        return toml.load(config)


def parse_args():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("input_path", type=str, help="input_path, where commands.csv is located")
    return parser.parse_args()


def run(commands, process):
    with ControlSender() as sender, Receiver() as receiver:
        print("Starting simulation loop")

        commands.append(Command('step', 0))
        commands.append(Command('step', 0))
        commands.append(Command('step', 0))
        for cmd in commands:
            # Check if the subprocess is still running
            if process.poll() is not None:
                print("Subprocess has terminated")
                break
            sender.send(cmd.command, cmd.zmq_flag)

            if cmd.command == "step":
                while not receiver.wait_for_constraints(timeout=100):
                    # Check if the subprocess is still running while waiting
                    if process.poll() is not None:
                        print("Subprocess has terminated while waiting for constraints")
                        return
            cmd.sent = True

        print("All commands sent, stopping")


def main(input_path):
    if os.path.isdir(input_path):
        input_dir = input_path
    elif os.path.isfile(input_path):
        if input_path.endswith(".tar.xz"):
            input_dir = input_path[:-len(".tar.xz")]
            with tarfile.open(input_path) as f:
                if hasattr(tarfile, "data_filter"):
                    f.extractall(".", filter="data")
                else:
                    f.extractall(".")
        else:
            raise RuntimeError(f"[ERROR] '{input_path}' is not managed")
    else:
        raise RuntimeError(f"[ERROR] '{input_path}' not found")

    config_file = os.path.join(input_dir, "config.toml")
    config_data = load_config(config_file)
    jobs_file = config_data.get("input_files", {}).get("job_file")
    if jobs_file is None:
        raise RuntimeError(f"[ERROR] 'job_file' not found in {config_file}")

    jobs_path = os.path.join(input_dir, jobs_file)

    if DYNAWO_SCRIPT is None:
        raise RuntimeError("[ERROR] DYNAWO_SCRIPT environment variable not set")

    print(f"Running Dynawo script: {DYNAWO_SCRIPT} jobs -i {jobs_path}")
    process = subprocess.Popen([DYNAWO_SCRIPT, "jobs", "-i", jobs_path])

    commands_file = os.path.join(input_dir, "commands.csv")
    commands = load_commands_from_csv(commands_file)
    run(commands, process)

    # End the subprocess after the run is complete
    if process.poll() is None:
        time.sleep(2)
        print("Stopping Dynawo subprocess...")
        process.kill()
        time.sleep(5)

if __name__ == "__main__":
    args = parse_args()
    main(args.input_path)
