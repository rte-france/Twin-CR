"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Mock Orchestrator implementation used in tests and local development.

It simulates the behavior of the production orchestrator so integration
scenarios can be exercised without the full runtime.
"""

import json
import asyncio
import os
import re
import signal
import logging
from typing import Dict, Optional
from pathlib import Path

import jsonschema
import nats.aio.msg
from nats.aio.client import Client as NATS
from nats.errors import NoRespondersError


logger = logging.getLogger("mock_orchestrator")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

def check_type(value, target_type: str):
    """
    Validate that a value matches the expected schema type definition.

    Args:
        value: Value to verify.
        target_type (str): Schema type name (e.g., 'string', 'double').

    Raises:
        ValueError: If the value does not match the schema type.
    """
    if target_type == "string":
        target = str
    elif target_type == "double":
        target = float
    elif target_type == "bool":
        target = bool
    else:
        raise NotImplementedError(f"{target_type} is not considered")

    if not isinstance(value, target):
        raise ValueError(f"{value} is not of type {target_type}")


async def nats_request(
    nats_connection: NATS, subject: str, message: bytes, timeout=2.0
):
    """
    Send a request via NATS and log the orchestrator's reply.

    Args:
        nats_connection (NATS): Connected client.
        subject (str): Subject to publish to.
        message (bytes): Encoded payload.
        timeout (float): Seconds to wait for a response.
    """
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


MAX_TIME = 500
PERIOD = 1


class OrchestratorMock:
    """Simplified orchestrator that publishes time and consumes control commands."""

    def __init__(self):
        """Initialize default state and load the communication-network fixtures."""
        self.time = 0
        self.nats_connection = NATS()
        self.dsl_subscriptions: Dict[str, Dict[str, Optional[str]]] = {}
        self.ready_event = asyncio.Event()
        with open(
            Path(__file__).parent.parent.parent.parent
            / "docs/orchestrator/examples/Nordic/cyber_config_fake.json"
        ) as f:
            self.communication_network = json.load(f)
        self.communication_nodes: set[str] = set()
        for link in self.communication_network["links"]:
            self.communication_nodes.add(link["from"])
            self.communication_nodes.add(link["to"])

        schema_path = Path(__file__).parent.parent.parent.parent / "schemas/Orchestrator/Requests/game_master_control.json"
        with open(schema_path) as f:
            self.schema = json.load(f)
        schema_dir = schema_path.parent.resolve()
        base_uri = schema_dir.as_uri() + "/"
        self.resolver = jsonschema.RefResolver(
            base_uri=base_uri,
            referrer=self.schema
        )

        # Metadata is only used in the mock
        self.metadata_log_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "simulation_metadata.log",  # for appending metadata from orchestrator
        )

    async def run(self):
        """Loop until MAX_TIME, publishing time ticks and measurements."""
        await self.ready_event.wait()
        while self.time < MAX_TIME:
            await asyncio.sleep(1)
            await self.advance_time()
            await asyncio.sleep(PERIOD)

    async def stop(self):
        """Publish a stop message and terminate the current process."""
        msg = {"status": "Stopped"}
        await self.nats_connection.publish("stop", json.dumps(msg).encode())
        os.kill(os.getpid(), signal.SIGTERM)

    async def advance_time(self):
        """Advance the simulation clock by one period and emit updates."""
        self.time += PERIOD
        await self._publish_time(self.time)
        await self._publish_measurements()

    async def _publish_time(self, current_time: float):
        """
        Publish a time update on the ``time`` subject.

        Args:
            current_time (float): Absolute time to broadcast.
        """
        self.time = float(current_time)
        msg = {"current_time": self.time}
        await self.nats_connection.publish("time", json.dumps(msg).encode())
        logger.info("Published time: %s", json.dumps(msg))

    async def _publish_measurements(self):
        """Publish placeholder measurement values for each subscription."""
        ordered_subs = sorted(self.dsl_subscriptions.items())
        for dynawo_id, entry in ordered_subs:
            payload = {"id": dynawo_id, "value": 1}
            await self.nats_connection.publish(
                "DSL_values", json.dumps(payload).encode()
            )
            logger.info("Published DSL_values: %s", json.dumps(payload))

    async def connect(self):
        """Connect to the configured NATS server and subscribe to control subjects."""
        url = os.getenv("NATS_URL", "nats://localhost:4222")
        await self.nats_connection.connect(url)
        await self.nats_connection.subscribe(
            "GameMasterControl.>", cb=self.message_handler
        )
        await self.nats_connection.subscribe(
            "GameMasterStatus", cb=self.status_handler
        )  # For info, not how the orchestrator is actually started

    def add_subscription(
        self, dynawo_id: str, *, measurement_key: Optional[str], iidm_id: Optional[str]
    ) -> None:
        """Track a Dynawo measurement subscription for future publishing."""
        self.dsl_subscriptions[dynawo_id] = {
            "measurement_key": measurement_key,
            "iidm_id": iidm_id,
        }

    def remove_subscription(self, dynawo_id: str) -> None:
        """Remove a previously tracked Dynawo subscription."""
        self.dsl_subscriptions.pop(dynawo_id, None)

    @staticmethod
    def iidm_to_dynawo(iidm_id: str, attribute: str) -> str:
        """
        Map an IIDM identifier to the corresponding Dynawo measurement id.
        Note: the actual orchestrator has more complex mapping and can return a different value from this mock

        Args:
            iidm_id (str): Source IIDM identifier.
            attribute (str): Attribute being controlled.

        Returns:
            str: Dynawo identifier.
        """
        return f"NETWORK_{iidm_id}_{attribute}"  # Might differ from actual mapping

    async def message_handler(self, msg: nats.aio.msg.Msg):
        """
        Handle control commands published on ``GameMasterControl.*`` subjects.

        Args:
            msg (nats.aio.msg.Msg): Received command message.
        """
        raw_payload = msg.data.decode()
        logger.info("%s received: %s", msg.subject, raw_payload)

        body = json.loads(raw_payload)

        metadata = None

        status = "OK"
        reply_payload = {"status": status}
        try:
            if not isinstance(body, dict):
                raise ValueError(
                    "Expect messages on 'GameMasterControl.>' to be published as json dicts (in the mock)"
                )
            jsonschema.validate(instance=body, schema=self.schema, resolver=self.resolver)

            if body.get("t_start") is not None:
                t_start = body["t_start"]
            elif body.get("t_start_from_now") is not None:
                t_start = self.time + body["t_start_from_now"]
            else:
                t_start = self.time

            command = body["command"]
            if command == "add_dsl_subscription_from_iidm":
                iidm_id = body["iidm_id"]
                attribute = body["attribute"]
                dynawo_id = self.iidm_to_dynawo(iidm_id, attribute)
                measurement_key = body.get("measurement_key")
                self.add_subscription(
                    dynawo_id, measurement_key=measurement_key, iidm_id=iidm_id
                )
                reply_payload = {"status": "OK", "reply": dynawo_id}

            elif command == "remove_dsl_subscription_from_iidm":
                iidm_id = body["iidm_id"]
                attribute = body["attribute"]
                dynawo_id = self.iidm_to_dynawo(iidm_id, attribute)
                self.remove_subscription(dynawo_id)
                reply_payload = {"status": "OK", "reply": dynawo_id}

            elif command == "remove_dsl_subscription":
                dynawo_id = body["id"]
                self.remove_subscription(dynawo_id)
                reply_payload = {"status": "OK"}

            elif command == "iidm_command":
                iidm_id = body["iidm_id"]
                attribute = body["attribute"]

                value = float(body["value"])
                logger.info(
                    json.dumps(
                        {
                            "iidm_command": {
                                "current_time": self.time,
                                "scheduled_time": t_start,
                                "iidm_id": iidm_id,
                                "attribute": attribute,
                                "value": value,
                                "metadata": metadata,
                            }
                        }
                    )
                )

            elif command == "change_network_characteristics":
                reply_payload = {"status": "OK"}
                links = body["links"]
                nodes = body["nodes"]
                # Validate links
                for link in links:
                    found = False
                    link_from = str(link["from"])
                    link_to = str(link["to"])
                    # Check link exists
                    for existing_link in self.communication_network["links"]:
                        if (
                            link_from == existing_link["from"]
                            and link_to == existing_link["to"]
                        ):
                            found = True
                            break
                    if not found:
                        reply_payload = {
                            "status": f"No link from {link_from} to {link_to} exists"
                        }
                # Validate nodes
                for node in nodes:
                    node = str(node)
                    if node not in self.communication_nodes:
                        reply_payload = {"status": f"{node} does not exist"}

            elif command == "stop":
                self.stop()

            else:
                status = "Unsupported command (note: the mock only supports part of the commands of the real orchestrator)"
                reply_payload = {"status": status}

        except Exception as e:
            status = str(e)
            reply_payload = {"status": status}

        if msg.reply:
            await msg.respond(json.dumps(reply_payload).encode())

    async def status_handler(self, msg: nats.aio.msg.Msg):
        """
        Listen for status updates to know when to start publishing time ticks.

        Args:
            msg (nats.aio.msg.Msg): Status payload produced by the GameMaster bridge.
        """
        try:
            raw = msg.data.decode()
            status_payload = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(str(e))
            return

        sim_status = status_payload.get("simulation", {}).get("status")
        if sim_status in {"ready", "running"}:
            if not self.ready_event.is_set():
                self.ready_event.set()

    @staticmethod
    def _value_subject(subscription_id: str) -> str:
        """
        Normalize a measurement key into the Value.* subject hierarchy.

        Args:
            subscription_id (str): Dynawo measurement identifier.

        Returns:
            str: Subject string for measurement replies.
        """
        token = (subscription_id or "unknown").strip()
        if not token:
            token = "unknown"
        token = re.sub(r"[^A-Za-z0-9_.-]", "_", token)
        return f"Value.{token}"


async def main():
    """Run the mock orchestrator until cancelled (used for manual testing)."""
    mock = OrchestratorMock()
    await mock.connect()
    await mock.run()


if __name__ == "__main__":
    asyncio.run(main())
