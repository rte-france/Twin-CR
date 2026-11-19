"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Sessions as Nomad jobs, when the session manager runs in the Nomad infrastructure (NOMAD_ADDR set).

Each session is a job of the session job (docs/infra/twincr-session.nomad.hcl, shipped in the image), submitted through
the Nomad HTTP API: the HCL is parsed by Nomad with the variables of the session (/v1/jobs/parse), then registered
(/v1/jobs). The job initializes the session itself (its session-init task calls /init of its configurator), and stays
up after the simulation (end or crash) until it is stopped here (archive, then stop). The launch does not wait: the
session monitor (session_service) follows the jobs of the sessions with progress().
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import requests
from fastapi import HTTPException

logger = logging.getLogger("uvicorn.error")

# Task of the session job that initializes the session (poststart, exits once /init succeeded)
INIT_TASK = "session-init"
# Port label of the configurator in the session job
CONFIGURATOR_PORT_LABEL = "configurator"
# Port labels of the Argus backends in the session job: they load the grid after the initialization before answering
# their /health, and Traefik only routes to them once healthy, so a session is ready for Argus once they answer
ARGUS_BACKEND_PORT_LABELS = ("scada_http", "gm_http")


# Progress of a session job (NomadSessionClient.progress)
WAITING = "waiting"  # Not placed yet (e.g. not enough resources in the cluster)
STARTING = "starting"  # Placed, the session is not initialized yet
INITIALIZED = "initialized"  # Initialized (session-init done), the Argus backends may still be starting
FAILED = "failed"
GONE = "gone"  # Stopped, or not found


@dataclass
class SessionProgress:
    phase: str
    detail: str


def session_job_id(session_id: int) -> str:
    return f"session-{session_id}"


class NomadSessionClient:
    def __init__(self, address: str, token: str, job_hcl_path: str, extra_variables: str = ""):
        self.address = address.rstrip("/")
        self.token = token
        self.job_hcl_path = Path(job_hcl_path)
        # HCL variable assignments added to those of each session (e.g. registry = "...", one per line)
        self.extra_variables = extra_variables

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        headers = {"X-Nomad-Token": self.token} if self.token else {}
        try:
            response = requests.request(method, f"{self.address}{path}", headers=headers, timeout=30, **kwargs)
        except requests.RequestException as exc:
            raise HTTPException(status_code=502, detail=f"Nomad is not reachable at {self.address}: {exc}")
        return response

    def _check(self, response: requests.Response, action: str) -> requests.Response:
        if not response.ok:
            raise HTTPException(
                status_code=502,
                detail=f"Nomad could not {action}: HTTP {response.status_code} {response.text.strip()}",
            )
        return response

    def submit(self, job_id: str, variables: dict[str, str]) -> None:
        """Parses the session job with the given variables (plus session_id = job_id) and registers it."""
        assignments = {"session_id": job_id, **variables}
        # A JSON string is a valid HCL string literal
        hcl_variables = "\n".join(f"{name} = {json.dumps(value)}" for name, value in assignments.items())
        if self.extra_variables:
            hcl_variables += "\n" + self.extra_variables
        job = self._check(self._request("POST", "/v1/jobs/parse", json={
            "JobHCL": self.job_hcl_path.read_text(),
            "Variables": hcl_variables,
            "Canonicalize": True,
        }), "parse the session job").json()
        self._check(self._request("POST", "/v1/jobs", json={"Job": job}), f"register the job {job_id}")
        logger.info(f"Session job {job_id} submitted")

    def _latest_allocation(self, job_id: str) -> dict | None:
        response = self._request("GET", f"/v1/job/{job_id}/allocations")
        if response.status_code == 404:
            return None
        allocations: list[dict] = self._check(response, f"list the allocations of {job_id}").json()
        if not allocations:
            return None
        return max(allocations, key=lambda allocation: allocation["CreateIndex"])

    def progress(self, job_id: str) -> "SessionProgress":
        """Where the job of a session stands, without waiting (followed by the session monitor of session_service)."""
        response = self._request("GET", f"/v1/job/{job_id}")
        if response.status_code == 404:
            return SessionProgress(GONE, "Session job not found")
        job = self._check(response, f"read the job {job_id}").json()
        if job.get("Stop"):
            return SessionProgress(GONE, "Session job stopped")

        allocation = self._latest_allocation(job_id)
        if allocation is None:
            if job.get("Status") == "dead":
                return SessionProgress(FAILED, "Session job ended before starting")
            return SessionProgress(WAITING, self._placement_detail(job_id))

        task_states = allocation.get("TaskStates") or {}
        failed = [name for name, state in task_states.items() if state["Failed"]]
        if failed or allocation["ClientStatus"] in ("failed", "lost"):
            reasons = "; ".join(
                f"{name}: {(task_states[name].get('Events') or [{}])[-1].get('DisplayMessage', '')}" for name in failed
            )
            return SessionProgress(FAILED, f"Session job {allocation['ClientStatus']}: {reasons}"
                                           f" (nomad alloc status {allocation['ID'][:8]})")
        if allocation["ClientStatus"] == "complete" or job.get("Status") == "dead":
            return SessionProgress(FAILED, "Session job ended")

        init_state = task_states.get(INIT_TASK)
        if init_state and init_state["State"] == "dead":
            return SessionProgress(INITIALIZED, "Starting the Argus backends")
        return SessionProgress(STARTING, "Starting the services of the session")

    def _placement_detail(self, job_id: str) -> str:
        """Why the job has no allocation yet: the resources Nomad lacks to place it, if that is the reason."""
        evaluations: list[dict] = self._check(self._request("GET", f"/v1/job/{job_id}/evaluations"),
                                              f"list the evaluations of {job_id}").json()
        exhausted: set[str] = set()
        for evaluation in evaluations:
            for metrics in (evaluation.get("FailedTGAllocs") or {}).values():
                exhausted.update((metrics.get("DimensionExhausted") or {}).keys())
        if exhausted:
            return f"Waiting for cluster resources ({', '.join(sorted(exhausted))} exhausted: stop another session)"
        return "Waiting for the session to be scheduled"

    def backends_ready(self, job_id: str) -> bool:
        """Whether the Argus backends of the session answer (they load the grid after the initialization)."""
        for label in ARGUS_BACKEND_PORT_LABELS:
            url = self._port_url(job_id, label)
            try:
                if url is None or not requests.get(f"{url}/health", timeout=5).ok:
                    return False
            except requests.RequestException:
                return False
        return True

    def _port_url(self, job_id: str, label: str) -> str | None:
        allocation = self._latest_allocation(job_id)
        if allocation is None:
            return None
        details = self._check(self._request("GET", f"/v1/allocation/{allocation['ID']}"),
                              f"read the allocation of {job_id}").json()
        ports = ((details.get("AllocatedResources") or {}).get("Shared") or {}).get("Ports") or []
        for port in ports:
            if port["Label"] == label:
                return f"http://{port['HostIP']}:{port['Value']}"
        return None

    def archive(self, job_id: str) -> None:
        """Requests the archive of the simulation of the session (skipped by the configurator if already done)."""
        configurator_url = self._port_url(job_id, CONFIGURATOR_PORT_LABEL)
        if configurator_url is None:
            logger.warning(f"No configurator found for {job_id}: its simulation is not archived")
            return
        try:
            # Archiving a long simulation (several GB) takes time: only the response may take long, not the connection
            response = requests.get(f"{configurator_url}/archive", timeout=(10, 3600))
            logger.info(f"Archive of {job_id}: HTTP {response.status_code} {response.text.strip()}")
        except requests.RequestException as exc:
            logger.error(f"Archive of {job_id} failed: {exc}")

    def stop(self, job_id: str, purge: bool = False) -> None:
        """Stops the job (kept in Nomad with its logs until garbage collected), or removes it with purge."""
        response = self._request("DELETE", f"/v1/job/{job_id}", params={"purge": "true"} if purge else None)
        if response.status_code == 404:
            logger.info(f"Session job {job_id} not found, nothing to stop")
            return
        self._check(response, f"stop the job {job_id}")
        logger.info(f"Session job {job_id} {'purged' if purge else 'stopped'}")
