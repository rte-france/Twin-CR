"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Shared IIDM utilities supporting DSL resolution and property lookups.

These helpers convert measurement units and retrieve component metadata
from cached IIDM network exports.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import orjson

from ..iidm_helper import extract_network_data, serialize_network_data
from ..clickhouse_client import StorageError, StorageNotFound, get_clickhouse_client

logger = logging.getLogger(__name__)


def to_seconds(value, unit):
    """Convert a time quantity into seconds.

    Parameters
    ----------
    value : float
        Numeric duration expressed in ``unit``.
    unit : str
        Name of the unit. Accepted values are seconds, minutes, or hours
        (singular or plural).

    Returns
    -------
    float
        Equivalent duration in seconds.

    Raises
    ------
    ValueError
        If ``unit`` is not recognised.
    """

    unit = unit.lower()
    if unit in ["second", "seconds"]:
        return value
    if unit in ["minute", "minutes"]:
        return value * 60
    if unit in ["hour", "hours"]:
        return value * 3600
    raise ValueError(f"Unknown time unit: {unit}")


def get_iidm_properties(
    artifact_id: str,
    component_type: str,
    attributes: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Fetch component metadata from the IIDM cache or underlying object store.

    Parameters
    ----------
    artifact_id : str
        Identifier of the IIDM artefact whose components should be listed.
    component_type : str
        Component category requested (e.g. ``"load"`` or ``"generator"``).
    attributes : list of str, optional
        Additional attribute names to request. Core attributes are always
        included even when this argument is omitted.

    Returns
    -------
    list of dict
        Collection of component dictionaries enriched with voltage level and
        tagging information.
    """

    prefix = f"{artifact_id}/"
    storage_client = get_clickhouse_client()
    bucket_name = getattr(storage_client, "bucket_name", "iidm-files")

    cached_name = f"{artifact_id}/network_data.json"
    network_data = None
    try:
        try:
            storage_client.stat_object(bucket_name, cached_name)
            cached_bytes = storage_client.get_file(cached_name)
            network_data = orjson.loads(cached_bytes)
            logger.debug("Loaded cached network data for %s", artifact_id)
        except StorageNotFound:
            network_data = None
        except StorageError as e:
            if getattr(e, "code", None) not in ("NoSuchKey", "NoSuchBucket"):
                logger.error("Failed to get cached network data %s: %s", cached_name, e)
                return []
            network_data = None
    except Exception as e:
        logger.error(
            "Corrupted or unreadable cached network data for %s: %s", artifact_id, e
        )
        network_data = None

    if network_data is None:
        try:
            objects = storage_client.list_objects(bucket_name, prefix=prefix, recursive=True)
            obj_names = [obj.object_name for obj in objects]
            logger.debug(
                "Found %d objects under %s: %s", len(obj_names), prefix, obj_names
            )
        except StorageError as e:
            logger.error("Failed to list objects under %s: %s", prefix, e)
            return []
        except Exception as e:
            logger.error("Unexpected error listing objects under %s: %s", prefix, e)
            return []

        iidm_obj = None
        for name in obj_names:
            lower = name.lower()
            if lower.endswith((".iidm", ".xiidm", ".xml", ".xz", ".xiidm.xz")):
                iidm_obj = name
                break

        if not iidm_obj:
            logger.error("No IIDM file found under %s", prefix)
            return []

        try:
            iidm_bytes = storage_client.get_file(iidm_obj)
            logger.debug(
                "Downloaded IIDM file %s (%d bytes)", iidm_obj, len(iidm_bytes)
            )
        except StorageError as e:
            logger.error("Could not fetch IIDM file %s: %s", iidm_obj, e)
            return []
        except Exception as e:
            logger.error("Unexpected error fetching IIDM file %s: %s", iidm_obj, e)
            return []

        try:
            network_data = extract_network_data(iidm_bytes)
        except Exception as e:
            logger.error("Failed to parse IIDM for %s: %s", artifact_id, e)
            return []

        try:
            data_bytes = serialize_network_data(network_data)
            storage_client.upload_file(cached_name, data_bytes)
            logger.debug("Cached network data to %s", cached_name)
        except Exception as e:
            logger.debug("Skipping cache write to %s: %s", cached_name, e)

    elements = network_data.get("elements", {})
    voltage_levels = elements.get("voltage_levels", [])

    component_map = {
        "load": "loads",
        "generator": "generators",
        "line": "lines",
        "switch": "switches",
        "bus": "buses",
        "busbarsection": "busbar_sections",
        "busbarSection": "busbar_sections",
        "battery": "batteries",
        "substation": "substations",
        "voltagelevel": "voltage_levels",
        "voltageLevel": "voltage_levels",
        "twowindingstransformer": "2_windings_transformers",
        "twoWindingsTransformer": "2_windings_transformers",
        "threewindingstransformer": "3_windings_transformers",
        "threeWindingsTransformer": "3_windings_transformers",
        "2_windings_transformer": "2_windings_transformers",
        "3_windings_transformer": "3_windings_transformers",
        "shunt": "shunt_compensators",
        "shunt_compensator": "shunt_compensators",
        "staticvarcompensator": "static_var_compensators",
        "staticVarCompensator": "static_var_compensators",
        "hvdcline": "hvdc_lines",
        "hvdcLine": "hvdc_lines",
    }
    normalized_type = (component_type or "").strip()
    key = component_map.get(normalized_type)
    if key is None:
        key = component_map.get(normalized_type.lower(), normalized_type)
    comps = elements.get(key, [])
    if not comps:
        logger.warning("No '%s' elements in network %s", component_type, artifact_id)
        return []

    default_attrs = [
        "name",
        "id",
        "p0",
        "q0",
        "p",
        "q",
        "target_p",
        "voltage_level_id",
        "substation_id",
        "i",
        "nominal_v",
        "connected",
        "tags",
    ]
    attrs = (
        default_attrs if attributes is None else list(set(attributes + default_attrs))
    )

    def normalize_id(vl_id):
        """Normalize voltage-level identifiers for consistent lookup keys."""
        if not vl_id:
            return vl_id
        return vl_id.lstrip("_").replace("_", " ").strip()

    v_lookup = {
        normalize_id(vl.get("id", vl.get("name"))): vl.get("nominal_v")
        for vl in voltage_levels
    }
    substation_lookup = {
        normalize_id(vl.get("id", vl.get("name"))): vl.get("substation_id")
        for vl in voltage_levels
    }

    out = []
    for idx, c in enumerate(comps):
        if not c.get("connected", True):
            logger.debug(
                "Skipping disconnected component: %s",
                c.get("name", c.get("id", "unknown")),
            )
            continue
        entry = {a: c.get(a) for a in attrs if a in c}
        component_id = c.get("id")
        if not component_id:
            logger.warning("Component at index %d missing 'id': %s", idx, c)
            component_id = f"temp_{component_type}_{idx}"
        entry["id"] = component_id
        vl = c.get("voltage_level_id")
        if vl:
            normalized_vl = normalize_id(vl)
            entry["nominal_v"] = v_lookup.get(normalized_vl)
            entry["substation_id"] = substation_lookup.get(normalized_vl, "")
        entry["tags"] = []
        if component_type == "load" and entry.get("p0", 0) > 50:
            entry["tags"].append("critical")
        if vl and v_lookup.get(normalized_vl) == 69.0:
            entry["tags"].append("high_voltage")
        out.append(entry)

    logger.debug(
        "Fetched %d '%s' components from IIDM %s", len(out), component_type, artifact_id
    )
    return out


__all__ = ["to_seconds", "get_iidm_properties"]
