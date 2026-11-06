"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
import asyncio
import os
import signal
import nats.aio.msg
from nats.aio.client import Client as NATS
from nats.errors import NoRespondersError

async def nats_request(nats_connection: NATS, subject: str, message: bytes, timeout=2.0):
    try:
        print("Sending", message, "to", subject)
        response = await nats_connection.request(subject, message, timeout)
        reply = json.loads(response.data.decode())
        if reply["status"] == "OK":
            print("Action implemented by orchestrator")
            return reply.get("reply")
        else:
            print("Error:", reply)
    except asyncio.TimeoutError:
        print("timeout")
    except NoRespondersError:
        print("No subscribers to", subject)


class DslServerMock:
    def __init__(self):
        self.time = 0
        self.nats_connection = NATS()

    async def connect(self):
        await self.nats_connection.connect("nats://localhost:4222")

        await self.nats_connection.subscribe("time", cb=self.time_message_handler)
        await self.nats_connection.subscribe("DSL_values", cb=self.value_message_handler)
        # Stop the server when the orchestrator finishes its simulation
        await self.nats_connection.subscribe("stop", cb=self.stop_message_handler)


    async def send_control(self, id, value):
        message = json.dumps({id: value}).encode()
        await nats_request(self.nats_connection, "GameMasterControl.DSL", message)


    async def ask_subscription(self, id):
        cmd = {
            "command": "add_dsl_subscription",
            "id": id
        }
        message = json.dumps(cmd).encode()
        await nats_request(self.nats_connection, "GameMasterControl.DSL", message)

    async def ask_subscription_from_iidm(self, iidm_id, attribute):
        cmd = {
            "command": "add_dsl_subscription_from_iidm",
            "iidm_id": iidm_id,
            "attribute": attribute,
        }
        message = json.dumps(cmd).encode()
        reply = await nats_request(self.nats_connection, "GameMasterControl.DSL", message)
        print(reply)


    async def time_message_handler(self, msg: nats.aio.msg.Msg):
        message = json.loads(msg.data.decode())
        self.time = float(message["current_time"])
        print("Current time:", self.time)


    async def value_message_handler(self, msg: nats.aio.msg.Msg):
        data = msg.data.decode()
        message = json.loads(data)
        for k, v in message.items():  # Should only contain one value (message formatted as {"id":value})
            id = k
            value = v
            print(id, value)
            # if value > 999:
            #     self.send_control("id", "value")


    async def stop_message_handler(self, msg: nats.aio.msg.Msg):
        print(msg.data.decode())
        os.kill(os.getpid(), signal.SIGTERM)


async def main():
    server = DslServerMock()
    await server.connect()

    once = True
    while True:
        if server.time > 0:  # Ensures orchestrator is running
            if once:
                await server.ask_subscription("NETWORK_Tr1011-4011_breaker2_state_value")
                await server.ask_subscription_from_iidm("g01", "P")
                once = False

        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
