"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Event-driven bridge between EventStore-backed simulator control and NATS.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from copy import deepcopy
from contextlib import suppress
from typing import Optional, Set

import orjson

import nats.aio.msg
from nats.aio.client import Client as NATS

from .command_logger import NATSCommandLogger
from ..simulator_control_service import (
    SimulationNotInitializedError,
    compute_simulator_control_commands,
)
from ...domain.controllers.global_instances import get_event_store
from ..status_service import get_gamemaster_status, get_simulation_metadata
from ..value_cache import update_value as cache_update_value, clear as clear_value_cache
from ...utils.clock import ClockRegressionError
from ..dependency_subscription import DependencySubscriptionManager
from .health import roundtrip_with_client
from ..dsl_logging import get_dsl_logger


logger = logging.getLogger(__name__)


class GameMasterNATSBridge:
    """Subscribe to simulation time announcements and publish control commands."""

    def __init__(
        self,
        *,
        nats_url: str = os.getenv("NATS_URL", "nats://localhost:4222"),
        time_subject: str = "time",
        control_subject: str = "GameMasterControl.DSL",
        trainer_control_subject: str = "GameMasterControl.Trainer_DSL",
        loop: Optional[asyncio.AbstractEventLoop] = None,
        status_subject: str = "GameMasterStatus",
        metadata_subject: str = "GameMasterMetadata",
        status_interval: float = 1.0,
        command_logger: Optional[NATSCommandLogger] = None,
    ) -> None:
        """
        Configure bridge subjects and runtime options.

        Args:
            nats_url (str): Connection URL for the NATS cluster.
            time_subject (str): Subject that publishes simulation time ticks.
            control_subject (str): Subject receiving DSL-originated commands.
            trainer_control_subject (str): Subject for trainer/user commands.
            loop (Optional[asyncio.AbstractEventLoop]): Event loop override.
            status_subject (str): Subject used when publishing service status.
            metadata_subject (str): Subject for simulation metadata.
            status_interval (float): Interval between status publications.
        """
        self._nats_url = nats_url
        self._time_subject = time_subject
        self._control_subject = control_subject
        self._trainer_control_subject = trainer_control_subject
        self._loop = loop
        self._status_subject = status_subject
        self._metadata_subject = metadata_subject
        self._status_interval = status_interval
        self._dependency_manager = DependencySubscriptionManager()
        self._measurement_timeout = 2.0
        self._measurement_to_dynawo: dict[str, str] = {}
        self._dynawo_to_measurement: dict[str, str] = {}
        self._measurement_details: dict[str, tuple[str, str, str]] = {}
        self._command_logger = command_logger
        self._logging_simulation_name: Optional[str] = None
        self._logging_active = False

        self._nc: Optional[NATS] = None
        self._sub_sid: Optional[int] = None
        self._status_task: Optional[asyncio.Task] = None
        self._value_sid: Optional[int] = None
        self._dsl_value_sid: Optional[int] = None
        self._clock_started = False
        self._simulation_ready = False
        self._ready_states = {"ready", "running"}
        self._active_simulation: Optional[str] = None
        self._measurement_subjects: dict[str, str] = {}
        self._time_sub = None
        self._value_sub = None
        self._dsl_value_sub = None
        self._latest_status: Optional[dict] = None
        self._latest_metadata: Optional[dict] = None

    @property
    def client(self) -> NATS:
        """
        Return the connected NATS client.

        Returns:
            nats.aio.client.Client: Active connection.

        Raises:
            RuntimeError: If `connect` has not been called yet.
        """
        if self._nc is None:
            raise RuntimeError("NATS client not connected")
        return self._nc

    async def connect(self) -> None:
        """Connect to NATS and subscribe to time, value, and DSL subjects."""
        if self._nc is not None:
            return
        self._nc = NATS()
        loop = self._loop or asyncio.get_running_loop()
        self._loop = loop
        await self._nc.connect(self._nats_url)
        self._time_sub = await self._nc.subscribe(
            self._time_subject, cb=self._on_time_tick
        )
        self._value_sub = await self._nc.subscribe("Value.>", cb=self._on_value_update)
        self._dsl_value_sub = await self._nc.subscribe(
            "DSL_values", cb=self._on_dsl_value
        )
        self._sub_sid = getattr(self._time_sub, "sid", self._time_sub)
        self._value_sid = getattr(self._value_sub, "sid", self._value_sub)
        self._dsl_value_sid = getattr(self._dsl_value_sub, "sid", self._dsl_value_sub)
        self._status_task = asyncio.create_task(self._publish_status_loop())
        logger.info(
            "GameMaster NATS bridge connected to %s, subscribed to '%s'",
            self._nats_url,
            self._time_subject,
        )

    async def close(self) -> None:
        """Unsubscribe, cancel background tasks, and close the NATS client."""
        if self._nc is None:
            return
        if self._status_task is not None:
            self._status_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._status_task
            self._status_task = None
        with suppress(Exception):
            await self._nc.close()
        self._nc = None
        self._sub_sid = None
        self._value_sid = None
        self._dsl_value_sid = None
        self._time_sub = None
        self._value_sub = None
        self._dsl_value_sub = None
        self._measurement_to_dynawo.clear()
        self._dynawo_to_measurement.clear()
        self._measurement_details.clear()
        self._clock_started = False
        self._latest_status = None
        self._latest_metadata = None
        self._logging_simulation_name = None
        self._logging_active = False
        logger.info("GameMaster NATS bridge disconnected")

    def reset_state(self) -> None:
        """Clear cached subscription state so a subsequent init starts fresh."""

        self._dependency_manager.reset()
        clear_value_cache()
        self._clock_started = False
        self._active_simulation = None
        self._measurement_to_dynawo.clear()
        self._dynawo_to_measurement.clear()
        self._measurement_details.clear()
        self._measurement_subjects.clear()
        self._latest_status = None
        self._latest_metadata = None
        self._logging_simulation_name = None
        self._logging_active = False

    async def _log_command_payload(
        self,
        *,
        subject: str,
        payload: dict,
        sim_time: Optional[float],
        source: Optional[str],
    ) -> None:
        if self._command_logger is None or not self._logging_active:
            return
        simulation_name = self._logging_simulation_name or self._active_simulation
        if not simulation_name:
            return
        try:
            await self._command_logger.record(
                simulation=simulation_name,
                sim_time=sim_time,
                subject=subject,
                source=source,
                payload=payload,
                reply=None,
            )
        except Exception:
            logger.debug("Failed to log NATS command payload", exc_info=True)

    async def _log_execution_status(
        self,
        *,
        event_id: Optional[str],
        succeeded: bool,
        sim_time: Optional[float],
        subject: str,
        command: Optional[dict],
        error: Optional[str] = None,
    ) -> None:
        if not event_id:
            return
        logger_instance = get_dsl_logger()
        if logger_instance is None:
            return
        simulation_name = self._logging_simulation_name or self._active_simulation
        metadata = {"subject": subject}
        if error:
            metadata["error"] = error
        command_text = None
        command_payload = None
        if isinstance(command, dict):
            command_payload = dict(command)
            command_payload.pop("_dsl_text", None)
            command_text = command.get("_dsl_text") or command.get("dsl_text")
            if command_text is None:
                meta = command.get("metadata")
                if isinstance(meta, dict):
                    command_text = meta.get("dsl_text")
        if command_text is None and isinstance(command, dict):
            try:
                command_text = json.dumps(command, default=str)
            except Exception:
                command_text = str(command)
        try:
            await logger_instance.record_execution_result(
                simulation=simulation_name,
                event_id=event_id,
                succeeded=succeeded,
                sim_time=sim_time,
                metadata={**metadata, "command": command_payload}
                if command_payload is not None
                else metadata,
                dsl_text=command_text,
            )
        except Exception:
            logger.debug(
                "Failed to record execution status for %s", event_id, exc_info=True
            )

    async def _on_time_tick(self, msg: nats.aio.msg.Msg) -> None:
        """
        Handle simulation time broadcasts and publish control commands.

        Args:
            msg (nats.aio.msg.Msg): NATS message containing ``current_time``.
        """
        try:
            payload = json.loads(msg.data.decode()) if msg.data else {}
        except json.JSONDecodeError:
            logger.warning("Received malformed time payload: %s", msg.data)
            return

        current_time = payload.get("current_time")
        if current_time is None:
            logger.debug("Ignoring time payload without 'current_time': %s", payload)
            return

        try:
            current_time = float(current_time)
        except (TypeError, ValueError):
            logger.warning("Invalid current_time value on time subject: %s", payload)
            return

        if not self._clock_started:
            self._clock_started = True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "First time tick received at %.3f; enabling DSL subscription sync",
                    current_time,
                )
            try:
                await self._sync_dependency_subscriptions(
                    self._latest_metadata, self._latest_status or {}
                )
            except Exception:
                logger.debug(
                    "Initial DSL subscription sync failed after clock start",
                    exc_info=True,
                )

        if not self._simulation_ready:
            logger.debug(
                "Skipping simulator control at %.3f because simulation is not ready",
                current_time,
            )
            return

        logger.debug("Processing simulator control for time %.3f", current_time)

        try:
            commands, simulation_name, completion_ids = compute_simulator_control_commands(
                current_time
            )
        except SimulationNotInitializedError as exc:
            logger.info("GameMaster not ready: %s", exc)
            return
        except ClockRegressionError as exc:
            logger.warning("Clock regression detected: %s", exc)
            return
        except Exception as exc:
            logger.error(
                "Failed to compute simulator control commands: %s", exc, exc_info=True
            )
            return

        if not commands:
            if completion_ids:
                try:
                    get_event_store().mark_completed(list(completion_ids))
                except Exception as exc:
                    logger.warning("Failed to mark completion events as completed: %s", exc)
            logger.debug("No commands to publish for time %.3f", current_time)
            return

        if simulation_name:
            self._logging_simulation_name = simulation_name

        prepared_batch = []

        for command in commands:
            prepared = self._prepare_command_for_publish(command)
            if prepared is None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Skipping command that could not be prepared: %s", command)
                continue

            event_id = None
            time_spec_val = None
            meta = command.get("metadata") if isinstance(command, dict) else None
            if isinstance(meta, dict):
                event_id = meta.get("event_id")
                time_spec_val = meta.get("time_spec")

            raw_id = prepared.get("iidm_id") or prepared.get("id") or "unknown"
            reply_subject = self._format_reply_subject(raw_id)
            publish_subject = self._subject_for_command(command)

            try:
                payload_bytes = orjson.dumps(prepared)
                log_payload = dict(prepared)
                log_payload.pop("_dsl_text", None)
                meta_for_publish = log_payload.get("metadata")
                if isinstance(meta_for_publish, dict):
                    log_payload["metadata"] = dict(meta_for_publish)
                    log_payload["metadata"].pop("dsl_text", None)
                body_for_publish = log_payload.get("payload")
                if isinstance(body_for_publish, dict):
                    log_payload["payload"] = dict(body_for_publish)
                    log_payload["payload"].pop("dsl_text", None)
            except Exception as exc:
                logger.warning("Failed to encode command with orjson: %s", exc)
                continue

            source = None
            if isinstance(meta, dict) and meta.get("source") is not None:
                source = str(meta.get("source")).strip().lower()
            if source is None:
                source = (
                    "trainer"
                    if publish_subject == self._trainer_control_subject
                    else "dsl"
                )

            prepared_batch.append({
                'subject': publish_subject,
                'payload': payload_bytes,
                'reply': reply_subject,
                'event_id': event_id,
                'time_spec': time_spec_val,
                'prepared': prepared,
                'command': command,
                'log_payload': log_payload,
                'source': source,
            })

        if not prepared_batch:
            logger.debug("No valid commands to publish for time %.3f", current_time)
            return

        BATCH_CHUNK_SIZE = 5000 # Adjust chunk size as needed for performance tuning depending on NATS server capabilities
        event_ids_to_complete = []
        event_ids_to_fail = []

        for chunk_start in range(0, len(prepared_batch), BATCH_CHUNK_SIZE):
            chunk = prepared_batch[chunk_start:chunk_start + BATCH_CHUNK_SIZE]

            publish_tasks = [
                self.client.publish(item['subject'], item['payload'], reply=item['reply'])
                for item in chunk
            ]

            logging_tasks = []

            try:
                results = await asyncio.gather(*publish_tasks, return_exceptions=True)

                for idx, result in enumerate(results):
                    item = chunk[idx]
                    logging_tasks.append(
                        self._log_command_payload(
                            subject=item["subject"],
                            payload=item["log_payload"],
                            sim_time=current_time,
                            source=item.get("source"),
                        )
                    )
                    event_id = item['event_id']
                    if event_id:
                        if isinstance(result, Exception):
                            event_ids_to_fail.append(event_id)
                            if logger.isEnabledFor(logging.WARNING):
                                logger.warning("Failed to publish command: %s", result)
                            logging_tasks.append(
                                self._log_execution_status(
                                    event_id=str(event_id),
                                    succeeded=False,
                                    sim_time=current_time,
                                    subject=item["subject"],
                                    command=item["command"],
                                    error=str(result),
                                )
                            )
                        else:
                            time_spec = str(item.get('time_spec') or '').lower()
                            should_complete = time_spec != 'interval'
                            if not should_complete:
                                meta = (
                                    item["command"].get("metadata")
                                    if isinstance(item.get("command"), dict)
                                    else None
                                )
                                interval_end = (
                                    meta.get("interval_end") if isinstance(meta, dict) else None
                                )
                                try:
                                    should_complete = (
                                        interval_end is not None
                                        and float(current_time) + 1e-9 >= float(interval_end)
                                    )
                                except (TypeError, ValueError):
                                    should_complete = False
                            if should_complete:
                                event_ids_to_complete.append(event_id)
                            logging_tasks.append(
                                self._log_execution_status(
                                    event_id=str(event_id),
                                    succeeded=True,
                                    sim_time=current_time,
                                    subject=item["subject"],
                                    command=item["command"],
                                )
                            )
            except Exception as exc:
                logger.error("Batch publish failed catastrophically: %s", exc)
                event_ids_to_fail.extend(item['event_id'] for item in chunk if item['event_id'])

            if logging_tasks:
                await asyncio.gather(*logging_tasks, return_exceptions=True)

        completed_ids = set(event_ids_to_complete) | set(completion_ids)
        if completed_ids:
            try:
                get_event_store().mark_completed(list(completed_ids))
            except Exception as exc:
                logger.warning("Failed to mark events as completed: %s", exc)

        if event_ids_to_fail:
            try:
                get_event_store().mark_failed(event_ids_to_fail, "Publish failed")
            except Exception as exc:
                logger.warning("Failed to mark events as failed: %s", exc)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Published %d commands for simulation %s at %.3f (succeeded: %d, failed: %d)",
                len(prepared_batch),
                simulation_name,
                current_time,
                len(event_ids_to_complete),
                len(event_ids_to_fail),
            )

    async def _publish_status_loop(self) -> None:
        """Continuously publish status, metadata, and manage subscriptions."""
        while True:
            try:
                nats_ok = await roundtrip_with_client(self.client)
                status = get_gamemaster_status(nats_healthy=nats_ok)
                sim_status = (status.get("simulation") or {}).get("status")
                self._simulation_ready = sim_status in self._ready_states
                sim_info = status.get("simulation") or {}
                orchestrator_sim_name = sim_info.get("name")
                if orchestrator_sim_name:
                    self._logging_simulation_name = orchestrator_sim_name
                if self._simulation_ready and not self._logging_active:
                    self._logging_active = True
                elif not self._simulation_ready:
                    self._logging_active = False
                await self.client.publish(
                    self._status_subject,
                    json.dumps(status).encode(),
                )
                logger.debug(
                    "Published GameMaster status to %s: %s",
                    self._status_subject,
                    status,
                )

                metadata = get_simulation_metadata()
                if metadata:
                    await self.client.publish(
                        self._metadata_subject,
                        json.dumps(metadata).encode(),
                    )
                    logger.debug(
                        "Published GameMaster metadata to %s: %s",
                        self._metadata_subject,
                        metadata,
                    )

                self._latest_status = status
                self._latest_metadata = metadata

                if not self._clock_started:
                    logger.debug(
                        "Deferring DSL subscription sync until orchestrator clock starts"
                    )
                else:
                    await self._sync_dependency_subscriptions(metadata, status)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "Failed to publish GameMaster status: %s", exc, exc_info=True
                )
            await asyncio.sleep(self._status_interval)

    async def _sync_dependency_subscriptions(
        self, metadata: Optional[dict], status: dict
    ) -> None:
        """
        Reconcile dependency-driven measurement subscriptions.

        Args:
            metadata (Optional[dict]): Latest simulation metadata payload.
            status (dict): Status payload emitted to NATS.
        """
        simulation_name = None
        if metadata and metadata.get("simulation"):
            simulation_name = metadata.get("simulation")
        elif status.get("simulation"):
            simulation_name = status["simulation"].get("name")

        if simulation_name and simulation_name != self._active_simulation:
            logger.debug(
                "Detected simulation change from %s to %s; resetting subscriptions and cache",
                self._active_simulation,
                simulation_name,
            )
            if self._active_simulation is not None:
                self._dependency_manager.reset()
                clear_value_cache()
                self._measurement_to_dynawo.clear()
                self._dynawo_to_measurement.clear()
            self._active_simulation = simulation_name
            self._logging_simulation_name = simulation_name

        to_add, to_remove = self._dependency_manager.sync()
        if not to_add and not to_remove:
            return

        meta_payload = {}
        if simulation_name:
            meta_payload["simulation"] = simulation_name
        if metadata and metadata.get("time_passed") is not None:
            meta_payload["time_passed"] = metadata.get("time_passed")

        tasks = [self._add_iidm_subscription(key) for key in sorted(to_add)]
        await asyncio.gather(*tasks)

        tasks = [self._remove_iidm_subscription(key) for key in sorted(to_remove)]
        await asyncio.gather(*tasks)

    async def ensure_measurement_subscription(
        self, measurement_key: str, meta_payload: Optional[dict] = None
    ) -> None:
        """Ensure a measurement key is actively subscribed for upcoming actions."""

        if not measurement_key:
            return
        if self._nc is None:
            logger.debug(
                "Skipping measurement subscription %s because NATS client is not connected",
                measurement_key,
            )
            return
        if measurement_key in self._measurement_to_dynawo:
            return

        metadata = dict(meta_payload or {})
        if self._active_simulation and "simulation" not in metadata:
            metadata["simulation"] = self._active_simulation
        source = None
        raw_source = metadata.get("source") if isinstance(metadata, dict) else None
        if raw_source is not None:
            source = str(raw_source).strip().lower()
        if measurement_key not in self._measurement_details:
            parsed = self._parse_measurement_key(measurement_key)
            if parsed:
                self._measurement_details[measurement_key] = parsed
        simulation_name = metadata.get("simulation", self._active_simulation)
        try:
            await self._add_iidm_subscription(measurement_key)
        except Exception:
            logger.debug(
                "Failed to eagerly subscribe measurement %s",
                measurement_key,
                exc_info=True,
            )
            return

        self._dependency_manager.record_subscription(
            measurement_key, simulation_name, source
        )

    async def _on_value_update(self, msg: nats.aio.msg.Msg) -> None:
        """
        Update the measurement cache when real-time values arrive.

        Args:
            msg (nats.aio.msg.Msg): NATS payload with ``id``/``value``.
        """
        try:
            data = json.loads(msg.data.decode()) if msg.data else {}
        except json.JSONDecodeError:
            logger.debug(
                "Discarding malformed value payload on %s: %s", msg.subject, msg.data
            )
            return

        key = data.get("id") or data.get("key")
        value = data.get("value")
        if key is None or value is None:
            return
        cache_update_value(str(key), value)

    async def _on_dsl_value(self, msg: nats.aio.msg.Msg) -> None:
        """
        Normalize DSL-specific value payloads into the shared cache.

        Args:
            msg (nats.aio.msg.Msg): Message keyed by dynawo identifiers.
        """
        try:
            data = json.loads(msg.data.decode()) if msg.data else {}
        except json.JSONDecodeError:
            logger.debug("Discarding malformed DSL value payload: %s", msg.data)
            return

        if not isinstance(data, dict):
            logger.debug("Ignoring non-dict DSL value payload: %s", data)
            return

        dynawo_id = data.get("id")
        raw_value = data.get("value")
        if not dynawo_id or not raw_value:
            logger.debug("Missing 'id' or 'value' field: %s", data)

        measurement_key = self._dynawo_to_measurement.get(str(dynawo_id))
        if measurement_key is None:
            inferred = self._infer_measurement_key(str(dynawo_id))
            if inferred:
                measurement_key = inferred
        if not measurement_key:
            logger.debug("Received DSL value for unknown dynawo id %s", dynawo_id)
            return
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            logger.debug("Non-numeric DSL value for %s: %s", dynawo_id, raw_value)
            return
        cache_update_value(measurement_key, value)

    async def request_with_retry(
        self, payload, *, subject: Optional[str] = None, max_retries=None, delay=1
    ):
        """
        Send a request to a subject, retrying with fixed delay on failure.

        Args:
            payload: JSON-serializable request body.
            subject (Optional[str]): Subject to publish to; defaults to
                the control subject.
            max_retries (Optional[int]): Maximum retries before failing.
            delay (int | float): Seconds to wait between retries.

        Returns:
            nats.aio.msg.Msg: Response message.

        Raises:
            Exception: Re-raises the last failure once retries are exhausted.
        """
        retries = 0
        while True:
            try:
                response = await self.client.request(
                    subject or self._control_subject,
                    json.dumps(payload).encode(),
                    timeout=self._measurement_timeout,
                )
                return response
            except Exception as exc:
                retries += 1
                if max_retries is not None and retries >= max_retries:
                    logger.warning(
                        "Request to %s failed after %d retries: %s",
                        subject or self._control_subject,
                        retries,
                        exc,
                    )
                    raise
                logger.debug(
                    "Request to %s failed (attempt %d), retrying in %ss: %s",
                    subject or self._control_subject,
                    retries,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)

    async def _add_iidm_subscription(self, measurement_key: str) -> None:
        """
        Request subscription updates so Dynawo publishes a measurement.

        Args:
            measurement_key (str): Canonical measurement identifier.
        """
        details = self._measurement_details.get(
            measurement_key
        ) or self._parse_measurement_key(measurement_key)
        if details is None:
            logger.debug(
                "Skipping DSL subscription for unsupported measurement key %s",
                measurement_key,
            )
            return
        attribute, element_type, iidm_id = details
        payload = {
            "command": "add_dsl_subscription_from_iidm",
            "iidm_id": iidm_id,
            "attribute": attribute,
            "element_type": element_type,
        }
        if measurement_key:
            payload["measurement_key"] = measurement_key

        subject = self._subject_for_measurement(measurement_key)
        try:
            response = await self.request_with_retry(payload, subject=subject)
        except asyncio.TimeoutError:
            return
        except Exception:
            return

        dynawo_id = self._process_subscription_reply(response, measurement_key)
        if dynawo_id is None:
            return
        self._measurement_to_dynawo[measurement_key] = dynawo_id
        self._dynawo_to_measurement[dynawo_id] = measurement_key
        self._measurement_details[measurement_key] = (attribute, element_type, iidm_id)
        self._measurement_subjects[measurement_key] = subject
        logger.debug(
            "Registered DSL subscription %s -> %s via %s",
            measurement_key,
            dynawo_id,
            subject,
        )

    async def _remove_iidm_subscription(self, measurement_key: str) -> None:
        """
        Request removal of a previously registered measurement subscription.

        Args:
            measurement_key (str): Canonical measurement identifier.
        """
        dynawo_id = self._measurement_to_dynawo.pop(measurement_key, None)
        if dynawo_id:
            self._dynawo_to_measurement.pop(dynawo_id, None)

        stored_details = self._measurement_details.pop(measurement_key, None)
        details = stored_details or self._parse_measurement_key(measurement_key)
        if details is None:
            logger.debug(
                "Skipping DSL unsubscribe for unsupported measurement key %s",
                measurement_key,
            )
            return
        attribute, element_type, iidm_id = details
        payload = {
            "command": "remove_dsl_subscription_from_iidm",
            "iidm_id": iidm_id,
            "attribute": attribute,
            "element_type": element_type,
            "measurement_key": measurement_key,
        }

        subject = self._measurement_subjects.pop(measurement_key, None)
        if subject is None:
            subject = self._subject_for_measurement(measurement_key)
        await self.client.publish(subject, json.dumps(payload).encode())

        logger.debug("Requested DSL subscription removal for %s", measurement_key)

    def _process_subscription_reply(
        self, response: nats.aio.msg.Msg, measurement_key: str
    ) -> Optional[str]:
        """
        Parse the bridge response to extract the Dynawo measurement id.

        Args:
            response (nats.aio.msg.Msg): Reply from the subscription request.
            measurement_key (str): Measurement key associated with the request.

        Returns:
            Optional[str]: Dynawo identifier when successful.
        """
        try:
            payload = json.loads(response.data.decode()) if response.data else {}
        except json.JSONDecodeError:
            logger.warning(
                "Invalid reply for DSL subscription %s: %s",
                measurement_key,
                response.data,
            )
            return None

        status = payload.get("status")
        if status != "OK":
            logger.warning(
                "DSL subscription request for %s failed: %s", measurement_key, payload
            )
            return None

        dynawo_id = payload.get("reply")
        if not dynawo_id:
            logger.warning(
                "DSL subscription reply missing dynawo id for %s: %s",
                measurement_key,
                payload,
            )
            return None
        return str(dynawo_id)

    @staticmethod
    def _parse_measurement_key(measurement_key: str) -> Optional[tuple[str, str, str]]:
        """
        Translate a measurement key into attribute, element type, and IIDM id.

        Args:
            measurement_key (str): Canonical measurement identifier.

        Returns:
            Optional[Tuple[str, str, str]]: Parsed components when the key
            follows the expected ``attr:element:id`` format.
        """
        if not measurement_key:
            return None
        parts = str(measurement_key).split(":", 2)
        if len(parts) != 3:
            return None
        attr_token, element_type, identifier = parts

        attr_token = attr_token.strip().lower()
        attr_map = {
            "power_active": "P",
            "power_reactive": "Q",
            "voltage": "V",
            "u": "V",
            "u_value": "V",
            "state": "state",
            "frequency": "F",
        }
        attribute = attr_map.get(attr_token, attr_token.upper())
        element_raw = element_type.strip()
        element_lookup = {
            "line": "line",
            "generator": "generator",
            "load": "load",
            "switch": "switch",
            "bus": "bus",
            "busbarsection": "busbarSection",
            "busbar_section": "busbarSection",
            "battery": "battery",
            "shunt": "shunt",
            "staticvarcompensator": "staticVarCompensator",
            "static_var_compensator": "staticVarCompensator",
            "voltagelevel": "voltageLevel",
            "voltage_level": "voltageLevel",
            "substation": "substation",
            "hvdcline": "hvdcLine",
            "hvdc_line": "hvdcLine",
            "twowindingstransformer": "twoWindingsTransformer",
            "two_windings_transformer": "twoWindingsTransformer",
            "threewindingstransformer": "threeWindingsTransformer",
            "three_windings_transformer": "threeWindingsTransformer",
        }
        element = element_lookup.get(element_raw.lower(), element_raw)
        identifier = identifier.strip()
        if not element or not identifier:
            return None
        return attribute, element, identifier

    @staticmethod
    def _format_reply_subject(raw_id: str) -> str:
        """
        Produce a sanitized reply subject for command acknowledgements.

        Args:
            raw_id (str): Device identifier extracted from the command.

        Returns:
            str: Subject under the `Value.*` hierarchy.
        """
        token = raw_id.strip() if isinstance(raw_id, str) else "unknown"
        if not token:
            token = "unknown"
        token = re.sub(r"[^A-Za-z0-9_.-]", "_", token)
        return f"Value.{token}"

    def _prepare_command_for_publish(self, command: dict) -> Optional[dict]:
        """
        Validate and sanitize a command prior to publishing it on NATS.

        Args:
            command (dict): Raw command generated by simulator_control.

        Returns:
            Optional[dict]: Cleaned command dict or ``None`` if invalid.
        """
        if not isinstance(command, dict):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Ignoring non-dict command payload: %s", command)
            return None

        name = command.get("command")
        if not name or not str(name).strip():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Command missing 'command' field: %s", command)
            return None

        name = str(name).strip()

        if name == "change_network_characteristics":
            links = command.get("links")
            nodes = command.get("nodes")

            normalized_links = []
            if isinstance(links, list):
                for link in links:
                    if not isinstance(link, dict):
                        continue
                    src = link.get("from")
                    dst = link.get("to")
                    if src is None or dst is None:
                        continue
                    normalized_links.append({"from": str(src), "to": str(dst)})

            normalized_nodes = []
            if isinstance(nodes, list):
                normalized_nodes = [
                    str(node)
                    for node in nodes
                    if node is not None and str(node).strip()
                ]

            if not normalized_links and not normalized_nodes:
                logger.warning(
                    "Network command missing link and node definitions: %s", command
                )
                return None

            prepared = {
                "command": name,
                "links": normalized_links,
                "nodes": normalized_nodes,
            }

            for optional_key in ("delay_function", "drop_function", "corruption_functions"):
                val = command.get(optional_key)
                if val is not None:
                    prepared[optional_key] = val

            if "t_start" in command:
                prepared["t_start"] = command["t_start"]

            return prepared
        else:
            prepared = command.copy()
            prepared.pop("metadata", None)
            return prepared

    def _subject_for_command(self, command: dict) -> str:
        """Select the publish subject based on the originating source metadata."""

        meta = command.get("metadata") if isinstance(command, dict) else None
        source = None
        if isinstance(meta, dict):
            raw_source = meta.get("source")
            if raw_source is not None:
                source = str(raw_source).strip().lower()
        return self._subject_for_source(source)

    def _subject_for_measurement(self, measurement_key: str) -> str:
        """
        Choose the publish subject based on a measurement key's sources.

        Args:
            measurement_key (str): Key tracked by the dependency manager.

        Returns:
            str: Subject string.
        """
        sources = self._dependency_manager.sources_for_key(measurement_key)
        return self._subject_for_sources(sources)

    def _subject_for_source(self, source: Optional[str]) -> str:
        """
        Resolve the subject when a single source label is available.

        Args:
            source (Optional[str]): Source label such as ``trainer``.

        Returns:
            str: Subject string.
        """
        return self._subject_for_sources({source} if source else set())

    def _subject_for_sources(self, sources: Set[str]) -> str:
        """
        Map a set of sources to the correct NATS subject.

        Args:
            sources (Set[str]): Source labels.

        Returns:
            str: Trainer-specific subject when any source references
            trainer events, otherwise the DSL control subject.
        """
        normalized = {str(s or "").strip().lower() for s in (sources or [])}
        if any(s.startswith("trainer") for s in normalized):
            return self._trainer_control_subject
        return self._control_subject

    def _infer_measurement_key(self, dynawo_id: str) -> Optional[str]:
        """
        Attempt to map a Dynawo measurement id back to a known measurement key.

        Args:
            dynawo_id (str): Identifier observed on DSL_values.

        Returns:
            Optional[str]: Matched measurement key when it can be inferred.
        """
        token = str(dynawo_id or "")
        if not token:
            return None
        if token in self._dynawo_to_measurement:
            return self._dynawo_to_measurement[token]

        suffix = token.lower()
        for key, details in self._measurement_details.items():
            if not isinstance(details, tuple) or len(details) != 3:
                continue
            attr, _, iidm_id = details
            if not iidm_id:
                continue
            if iidm_id not in token:
                continue
            attr_token = str(attr or "").lower()
            if attr_token and suffix.endswith(f"_{attr_token}"):
                self._dynawo_to_measurement[token] = key
                self._measurement_to_dynawo[key] = token
                return key
        return None


async def main() -> None:
    """Run the NATS bridge in a standalone event loop for local testing."""
    bridge = GameMasterNATSBridge()
    await bridge.connect()
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Shutting down GameMaster NATS bridge")
    finally:
        await bridge.close()


if __name__ == "__main__":
    asyncio.run(main())
