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
up after the simulation (end or crash) until it is stopped here (archive, then stop).
"""

import json
import logging
import time
from pathlib import Path

import requests
from fastapi import HTTPException

logger = logging.getLogger("uvicorn.error")

# Task of the session job that initializes the session (poststart, exits once /init succeeded)
INIT_TASK = "session-init"
# Port label of the configurator in the session job
CONFIGURATOR_PORT_LABEL = "configurator"


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

    def wait_initialized(self, job_id: str, timeout: float) -> None:
        """Waits for the session-init task of the job to succeed, raising if the session fails or times out."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            allocation = self._latest_allocation(job_id)
            if allocation is not None:
                task_states = allocation.get("TaskStates") or {}
                init_state = task_states.get(INIT_TASK)
                if init_state and init_state["State"] == "dead" and not init_state["Failed"]:
                    logger.info(f"Session job {job_id} initialized")
                    return
                failed = [name for name, state in task_states.items() if state["Failed"]]
                if failed or allocation["ClientStatus"] in ("failed", "lost"):
                    reasons = "; ".join(
                        f"{name}: {(task_states[name].get('Events') or [{}])[-1].get('DisplayMessage', '')}"
                        for name in failed
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=f"Session job {job_id} failed ({allocation['ClientStatus']}): {reasons}"
                               f" (see: nomad alloc status {allocation['ID'][:8]})",
                    )
            time.sleep(2)
        raise HTTPException(status_code=504, detail=f"Session job {job_id} not initialized after {timeout:.0f} s")

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
