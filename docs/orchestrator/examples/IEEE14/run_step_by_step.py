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
import time

import nats.aio.msg
from nats.aio.client import Client as NATS
from nats.errors import NoRespondersError

CONTROL_TOPIC = "GameMasterControl.TrainerAgent"

async def nats_request(nats_connection: NATS, subject: str, message: bytes, timeout=2.0):
    try:
        print("Sending", message, "to", subject)
        response = await nats_connection.request(subject, message, timeout)
        reply = json.loads(response.data.decode())
        if reply["status"] == "OK":
            print("Action implemented by orchestrator")
        else:
            print("Error:", reply)
    except asyncio.TimeoutError:
        print("timeout")
    except NoRespondersError:
        print("No subscribers to", subject)


PERIOD = 10
MAX_TIME = 1000

class Runner:
    async def __init__(self):
        nats_url = os.getenv("NATS_URL", "nats://localhost:4222")
        self.nats_connection = NATS()
        print(f"Connecting to NATS server: {nats_url}")
        await self.nats_connection.connect(nats_url)

        self.time = 0
        self.nats_connection.subscribe("time", cb=self.time_message_handler)

    async def go_to_next_period(self, next_period: float):
        # Schedule pause at next time step
        message = json.dumps({"t_start": float(next_period), "command": "pause"}).encode()
        await nats_request(self.nats_connection, CONTROL_TOPIC, message)
        # Fast forward to next time step
        message = json.dumps({"command": "fast_forward"}).encode()
        await nats_request(self.nats_connection, CONTROL_TOPIC, message)


    async def time_message_handler(self, msg: nats.aio.msg.Msg):
        message = json.loads(msg.data.decode())
        self.time = float(message["current_time"])
        print("Current time:", self.time)


    async def run(self):
        next_time = PERIOD
        while next_time < MAX_TIME:
            self.go_to_next_period(next_time)

            while (self.time < next_time):
                time.sleep(0.1)

            # TODO: implement action if necessary

            next_time += PERIOD


if __name__ == "__main__":
    runner = Runner()
    runner.run()
