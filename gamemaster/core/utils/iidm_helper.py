"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Utilities for loading IIDM networks and serializing derived metadata.

The helpers here normalize different input sources, extract structured
information, and provide serialization routines for cached responses.
"""

import pypowsybl as pp
import pandas as pd
import lzma
import orjson

from io import BytesIO
from typing import Dict, Any, Union, List
from datetime import timedelta
import tempfile
import logging
import os

# Module-level logger; configuration is handled by the application entry point
logger = logging.getLogger(__name__)


def extract_network_data(
    iidm_file: Union[str, bytes, pp.network.Network],
) -> Dict[str, Any]:
    """
    Load an IIDM network (from bytes, path, or network instance) and extract metadata.

    Args:
        iidm_file (Union[str, bytes, pp.network.Network]): Source IIDM content.

    Returns:
        Dict[str, Any]: Structured dictionary containing network properties,
        elements, and relationship data.

    Raises:
        ValueError: When the IIDM content cannot be read or is invalid.
    """
    try:
        logger.info("Starting IIDM file processing, input type: %s", type(iidm_file))

        network = None
        temp_file_path = None

        if hasattr(iidm_file, "get_generators"):
            # Caller already provided a loaded Network instance
            network = iidm_file  # type: ignore[assignment]
        else:
            # Handle bytes / file path inputs
            if isinstance(iidm_file, bytes):
                if iidm_file.startswith(b"\xfd7zXZ\x00"):
                    logger.debug("Detected XZ-compressed file, decompressing...")
                    try:
                        with lzma.open(BytesIO(iidm_file), "rb") as f:
                            xml_data = f.read()
                    except lzma.LZMAError as e:
                        logger.error("Failed to decompress XZ file: %s", e)
                        raise ValueError("Failed to decompress XZ file") from e
                else:
                    logger.debug("Assuming uncompressed XML file")
                    xml_data = iidm_file

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".xiidm"
                ) as temp_file:
                    temp_file.write(xml_data)
                    temp_file_path = temp_file.name
            else:
                temp_file_path = iidm_file
                if iidm_file.endswith(".xz"):
                    logger.debug("Input is XZ-compressed file path, decompressing...")
                    with lzma.open(iidm_file, "rb") as f:
                        xml_data = f.read()
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=".xiidm"
                    ) as temp_file:
                        temp_file.write(xml_data)
                        temp_file_path = temp_file.name

            try:
                logger.debug("Loading network from %s", temp_file_path)
                network = pp.network.load(temp_file_path)
                if network is None:
                    logger.error("Failed to load IIDM file: Invalid or corrupted file")
                    raise ValueError(
                        "Failed to load IIDM file: Invalid or corrupted file."
                    )
            finally:
                if temp_file_path and (
                    isinstance(iidm_file, bytes) or temp_file_path != iidm_file
                ):
                    try:
                        os.unlink(temp_file_path)
                        logger.debug("Deleted temporary file: %s", temp_file_path)
                    except OSError as e:
                        logger.warning(
                            "Failed to delete temporary file %s: %s", temp_file_path, e
                        )

        if network is None:
            raise ValueError("Unable to load IIDM network")

        logger.info("IIDM file loaded successfully")
        result = {
            "network_properties": {},
            "elements": {},
            "relationships": {
                "terminals": [],
                "voltage_levels": [],
                "substations": [],
                "topology": {},
            },
        }

        # Extract network properties
        result["network_properties"] = {
            "id": getattr(network, "id", None),
            "name": getattr(network, "name", None),
            "source_format": getattr(network, "source_format", None),
            "case_date": (
                str(network.case_date)
                if hasattr(network, "case_date") and network.case_date
                else None
            ),
            "forecast_distance": getattr(network, "forecast_distance", None),
            "per_unit": getattr(network, "per_unit", None),
            "nominal_apparent_power": getattr(network, "nominal_apparent_power", None),
        }
        missing_properties = [
            k for k, v in result["network_properties"].items() if v is None
        ]
        logger.info(
            "Extracted network properties: %d fields, missing: %s",
            len(result["network_properties"]),
            missing_properties or "none",
        )

        def _df_to_records(df: pd.DataFrame, element_name: str) -> List[Dict[str, Any]]:
            """
            Convert a pypowsybl dataframe into a list of serializable dicts.

            Args:
                df (pd.DataFrame): Dataframe returned by a network getter.
                element_name (str): Identifier used to tweak normalization.

            Returns:
                List[Dict[str, Any]]: Element records safe for JSON encoding.
            """
            if df is None or df.empty:
                return []

            working = df.copy()
            working = working.where(pd.notnull(working), None)

            records_df = working.reset_index(drop=False)
            index_col = records_df.columns[0]
            records_df.rename(columns={index_col: "__record_id__"}, inplace=True)

            if "id" in records_df.columns:
                records_df["id"] = records_df["id"].where(
                    records_df["id"].notnull(), records_df["__record_id__"]
                )
                records_df.loc[records_df["id"] == "", "id"] = records_df.loc[
                    records_df["id"] == "", "__record_id__"
                ]
                records_df.drop(columns=["__record_id__"], inplace=True)
            else:
                records_df.insert(0, "id", records_df.pop("__record_id__"))

            if element_name == "voltage_levels":
                records_df["id"] = records_df.apply(
                    lambda row: row["substation_id"] if not row["id"] else row["id"],
                    axis=1,
                )
            elif element_name == "substations":
                records_df["id"] = records_df.apply(
                    lambda row: (
                        row["name"]
                        if (not row["id"] and row.get("name"))
                        else row["id"]
                    ),
                    axis=1,
                )
                if "geo_tags" in records_df.columns:
                    records_df.rename(columns={"geo_tags": "tags"}, inplace=True)

            filled = records_df.where(pd.notnull(records_df), None)
            return filled.to_dict(orient="records")

        element_getters = {
            "2_windings_transformers": network.get_2_windings_transformers,
            "3_windings_transformers": network.get_3_windings_transformers,
            "aliases": network.get_aliases,
            "areas": network.get_areas,
            "batteries": network.get_batteries,
            "branches": network.get_branches,
            "busbar_sections": network.get_busbar_sections,
            "buses": network.get_buses,
            "bus_breaker_view_buses": network.get_bus_breaker_view_buses,
            "dangling_lines": network.get_dangling_lines,
            "generators": network.get_generators,
            "hvdc_lines": network.get_hvdc_lines,
            "identifiables": network.get_identifiables,
            "injections": network.get_injections,
            "lcc_converter_stations": network.get_lcc_converter_stations,
            "lines": network.get_lines,
            "loads": network.get_loads,
            "linear_shunt_compensator_sections": network.get_linear_shunt_compensator_sections,
            "non_linear_shunt_compensator_sections": network.get_non_linear_shunt_compensator_sections,
            "operational_limits": network.get_operational_limits,
            "phase_tap_changers": network.get_phase_tap_changers,
            "ratio_tap_changers": network.get_ratio_tap_changers,
            "shunt_compensators": network.get_shunt_compensators,
            "static_var_compensators": network.get_static_var_compensators,
            "substations": network.get_substations,
            "switches": network.get_switches,
            "voltage_levels": network.get_voltage_levels,
            "vsc_converter_stations": network.get_vsc_converter_stations,
            "tie_lines": network.get_tie_lines,
        }

        element_frames: Dict[str, pd.DataFrame] = {}

        for element_name, getter in element_getters.items():
            try:
                df = getter()
                element_frames[element_name] = df
                records = _df_to_records(df, element_name)
                result["elements"][element_name] = records
                logger.info("Extracted %s: %d records", element_name, len(records))
            except Exception as e:
                logger.warning("Failed to extract %s: %s", element_name, str(e))
                result["elements"][element_name] = []
                element_frames[element_name] = pd.DataFrame()

        # Simplified terminal extraction
        connectable_types = [
            "lines",
            "2_windings_transformers",
            "3_windings_transformers",
            "generators",
            "loads",
            "shunt_compensators",
            "busbar_sections",
            "batteries",
            "dangling_lines",
            "static_var_compensators",
            "lcc_converter_stations",
            "vsc_converter_stations",
        ]
        terminals = []
        for element_type in connectable_types:
            records = result["elements"].get(element_type, [])
            if not records:
                continue
            for record in records:
                element_id = record.get("id")
                terminal_info = {
                    "element_type": element_type.upper(),
                    "element_id": element_id,
                    "bus_id": None,
                    "voltage_level_id": record.get("voltage_level_id"),
                    "side": "",
                    "connected": record.get("connected", True),
                }
                terminals.append(terminal_info)
                result["relationships"]["terminals"].append(terminal_info)
        result["elements"]["terminals"] = terminals
        logger.info(
            "Extracted terminals relationships: %d entries",
            len(result["relationships"]["terminals"]),
        )

        # Extract voltage levels and substations relationships
        voltage_levels = result["elements"].get("voltage_levels", [])
        for vl in voltage_levels:
            if "id" not in vl or not vl["id"]:
                logger.warning("Voltage level missing 'id': %s", vl)
                continue
            try:
                vl_id = vl["id"]
                bus_ids = [
                    bus["id"]
                    for bus in result["elements"].get("buses", [])
                    if bus.get("voltage_level_id") == vl_id
                ]
                substation_id = vl.get("substation_id")
                vl_info = {
                    "voltage_level_id": vl_id,
                    "bus_ids": bus_ids,
                    "substation_id": substation_id,
                }
                result["relationships"]["voltage_levels"].append(vl_info)
                logger.info(
                    "Extracted voltage level %s: %d bus IDs, substation ID: %s",
                    vl_id,
                    len(bus_ids),
                    substation_id or "none",
                )
            except Exception as e:
                logger.warning("Failed to process voltage level %s: %s", vl, str(e))
        logger.info(
            "Extracted voltage levels relationships: %d entries",
            len(result["relationships"]["voltage_levels"]),
        )

        substations = result["elements"].get("substations", [])
        for sub in substations:
            if "id" not in sub or not sub["id"]:
                logger.warning("Substation missing 'id': %s", sub)
                continue
            try:
                sub_id = sub["id"]
                vl_ids = [
                    vl["id"]
                    for vl in voltage_levels
                    if vl.get("substation_id") == sub_id
                ]
                sub_info = {"substation_id": sub_id, "voltage_level_ids": vl_ids}
                result["relationships"]["substations"].append(sub_info)
                logger.info(
                    "Extracted substation %s: %d voltage level IDs", sub_id, len(vl_ids)
                )
            except Exception as e:
                logger.warning("Failed to process substation %s: %s", sub, str(e))
        logger.info(
            "Extracted substations relationships: %d entries",
            len(result["relationships"]["substations"]),
        )

        return result

    except Exception as e:
        logger.error("Error processing IIDM file: %s", str(e))
        raise


def serialize_network_data(data: Dict[str, Any]) -> bytes:
    """
    Serialize extracted network data to JSON bytes suitable for caching.

    Args:
        data (Dict[str, Any]): Structured network dictionary.

    Returns:
        bytes: UTF-8 encoded JSON representation.
    """

    def default_serializer(obj):
        """
        Convert unsupported objects (e.g., timedelta) into JSON-friendly values.

        Args:
            obj: Object encountered by the serializer.

        Returns:
            str | float: Converted representation.
        """
        if isinstance(obj, timedelta):
            return obj.total_seconds()
        return str(obj)

    return orjson.dumps(
        data, default=default_serializer, option=orjson.OPT_SERIALIZE_NUMPY
    )
