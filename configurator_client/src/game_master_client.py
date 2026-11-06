"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests

"""
Copy of gamemaster/core/mock/gm_mock_setup.py
TODO : uv-ify the gamemaster to allow editable import and avoid copy pasting
TODO : use nats events in gamemaster to get the context files
"""
class GameMasterClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout_s: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout_s
        # Default headers; 'requests' sets multipart Content-Type automatically.
        self.session.headers.update({"accept": "application/json"})

    def upload_iidm(self, iidm_path: Path, artifact_id: str) -> Dict[str, Any]:
        """POST /iidm/iidm/upload?artifact_id=... with multipart file."""
        url = f"{self.base_url}/iidm/iidm/upload"
        params = {"artifact_id": artifact_id}
        if not iidm_path.is_file():
            raise FileNotFoundError(f"IIDM file not found: {iidm_path}")

        with iidm_path.open("rb") as f:
            files = {"file": (iidm_path.name, f, "application/octet-stream")}
            resp = self.session.post(url, params=params, files=files, timeout=self.timeout)
        self._raise_for_bad_response(resp, "IIDM upload failed")
        return resp.json()

    def init_simulation(
        self,
        dsl_path: Path,
        simulation_name: str,
        artifact_id: str,
    ) -> Dict[str, Any]:
        """POST /trainer/init with DSL file and form fields."""
        url = f"{self.base_url}/trainer/init"
        if not dsl_path.is_file():
            raise FileNotFoundError(f"DSL file not found: {dsl_path}")

        with dsl_path.open("rb") as f:
            files = {"dsl_file": (dsl_path.name, f, "application/octet-stream")}
            data = {
                "simulationName": simulation_name,
                "artifact_id": artifact_id,
            }
            resp = self.session.post(url, files=files, data=data, timeout=self.timeout)
        self._raise_for_bad_response(resp, "Simulation init failed")
        return resp.json()

    def post_dsl_command(self, dsl_command: str) -> Dict[str, Any]:
        """POST /trainer/dsl_command with DSL command."""
        url = f"{self.base_url}/trainer/dsl_command"
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        resp = self.session.post(url, data=dsl_command.encode("utf-8"), headers=headers, timeout=self.timeout)
        return resp.json()

    @staticmethod
    def _raise_for_bad_response(resp: requests.Response, context: str) -> None:
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            details: Optional[str]
            try:
                details = json.dumps(resp.json(), ensure_ascii=False)
            except Exception:
                details = resp.text
            raise RuntimeError(f"{context}: HTTP {resp.status_code}: {details}") from e
