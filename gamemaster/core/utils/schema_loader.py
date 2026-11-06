"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Load cached JSON schemas used to validate simulation requests.

The helpers expose simple functions that read schema files from the
repository and cache them for repeated validation calls.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


_SCHEMA_DIR = Path(__file__).resolve().parent / "schema"


def _load_schema(filename: str) -> Dict[str, Any]:
    """
    Load a JSON schema file relative to the payload schema directory.

    Args:
        filename (str): Schema filename within the schema directory.

    Returns:
        Dict[str, Any]: Parsed JSON schema.

    Raises:
        RuntimeError: If the file is missing or invalid JSON.
    """
    path = _SCHEMA_DIR / filename
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Schema file '{filename}' not found in {_SCHEMA_DIR}."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Schema file '{filename}' is not valid JSON.") from exc


@lru_cache(maxsize=None)
def load_simulation_config_schema() -> Dict[str, Any]:
    """
    Return the cached schema for the simulator configuration payload.

    Returns:
        Dict[str, Any]: JSON schema describing AggregateOutput.
    """
    return _load_schema("schema.json")


@lru_cache(maxsize=None)
def load_iidm_command_schema_v2() -> Dict[str, Any]:
    """
    Return the cached schema used for v2 IIDM commands.

    Returns:
        Dict[str, Any]: JSON schema loaded from ``schema_v2.json``.
    """
    return _load_schema("schema_v2.json")
