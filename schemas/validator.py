"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
import sys
from pathlib import Path

from jsonschema import validate, ValidationError, SchemaError

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(json_file, schema_file):
    print(f"Validating {json_file} against {schema_file}", end=' ')
    try:
        data = load_json(json_file)
        schema = load_json(schema_file)

        validate(instance=data, schema=schema)
        print("✅")
        return True

    except FileNotFoundError as e:
        print(f"❌ File not found: {e.filename}")
        return False

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False

    except ValidationError as e:
        print("❌ JSON validation failed:")
        print(f"Message: {e.message}")
        print(f"Path: {'/'.join(map(str, e.path))}")
        return False

    except SchemaError as e:
        print("❌ Invalid JSON schema:")
        print(e)
        return False

EXAMPLES = Path(__file__).parent.parent / "docs" / "orchestrator" / "examples"

SCHEMAS = ["game_master_inputs.json", "game_master_outputs.json", "scada_outputs.json", "scada_inputs.json"]

# Every example the configurator has been run on (./cfg.sh in that folder), plus the hand-written 4Bus_PSCC
SCENARIOS = ["Nordic", "4Bus", "IEEE14", "4Bus_PSCC"]


def generated_file(scenario, schema_file):
    """
    Return the file of that scenario to validate against the schema.

    The configurator names the SCADA files with a _no_map suffix when the scenario has no cyber
    network and mapping, so the two spellings are tried in turn.
    """
    path = EXAMPLES / scenario / schema_file
    if path.exists():
        return path
    return path.with_name(f"{path.stem}_no_map{path.suffix}")


if __name__ == "__main__":
    all_valid = True
    for scenario in SCENARIOS:
        for schema_file in SCHEMAS:
            all_valid &= main(generated_file(scenario, schema_file), Path(__file__).parent / schema_file)
    sys.exit(0 if all_valid else 1)
