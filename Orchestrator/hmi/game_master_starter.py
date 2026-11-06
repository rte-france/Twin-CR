"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests

"""
Copy of gamemaster/core/mock/gm_mock_setup.py
"""
class GameMasterClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout_s: float = 30.0):
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


def prepare_simulation(
    iidm_path: str,
    dsl_path: str,
    artifact_id: str,
    base_url: str = "http://localhost:8000",
    simulation_name: Optional[str] = None,
    timeout_s: float = 30.0,
) -> Dict[str, Any]:
    """
    Convenience wrapper:
    1) Upload IIDM, 2) Initialize simulation with DSL.
    Returns a dict with both responses.
    """
    sim_name = simulation_name or artifact_id
    client = GameMasterClient(base_url=base_url, timeout_s=timeout_s)

    iidm_resp = client.upload_iidm(Path(iidm_path), artifact_id=artifact_id)
    # Use the artifact_id from server if provided; otherwise keep the caller's.
    effective_artifact = iidm_resp.get("artifact_id", artifact_id)

    init_resp = client.init_simulation(
        Path(dsl_path), simulation_name=sim_name, artifact_id=effective_artifact
    )

    return {"iidm_upload": iidm_resp, "init": init_resp}


def _cli() -> int:
    p = argparse.ArgumentParser(
        description="Upload IIDM and initialize simulation on GameMaster FastAPI."
    )
    p.add_argument("--base-url", default="http://localhost:8000", help="FastAPI base URL")
    p.add_argument("--artifact-id", required=True, help="Artifact ID (e.g., Nordic)")
    p.add_argument("--iidm", required=True, help="Path to IIDM file (e.g., Nordic.xiidm)")
    p.add_argument("--dsl", required=True, help="Path to DSL file (e.g., Nordic.dsl)")
    p.add_argument(
        "--simulation-name",
        default=None,
        help="Simulation name; defaults to artifact_id if omitted.",
    )
    p.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    args = p.parse_args()

    try:
        result = prepare_simulation(
            iidm_path=args.iidm,
            dsl_path=args.dsl,
            artifact_id=args.artifact_id,
            base_url=args.base_url,
            simulation_name=args.simulation_name,
            timeout_s=args.timeout,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # Example usage: direct script run
    #
    # Example command:
    #   python gm_setup.py \
    #       --base-url http://localhost:8000 \
    #       --artifact-id Nordic \
    #       --iidm Nordic.xiidm \
    #       --dsl Nordic.dsl \
    #       --simulation-name Nordic
    #
    # Example Python usage (from another module):
    #
    # from gm_setup import prepare_simulation

    result = prepare_simulation(
          iidm_path="../../docs/orchestrator/examples/Nordic/Nordic.xiidm",
          dsl_path="../../docs/orchestrator/examples/Nordic/Nordic.dsl",
          artifact_id="Nordic",
          base_url="http://localhost:8000"
      )
    print(result)

    # sys.exit(_cli())