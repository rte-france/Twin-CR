"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import zmq


class ActionSender:
    def __init__(self, address="tcp://localhost:5555"):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(address)

    def send(self, message):
        print(f"Sending action: {message}")
        self.socket.send_string(message)

        # Wait for acknowledgment
        message = self.socket.recv_string()
        print(f"return received: {message}")
