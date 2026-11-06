"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Check that the DSL test resources are the Nordic example's files (see README.md), once its cfg.sh has been run:
- Nordic.xiidm and game_master_outputs.json are plain copies
- game_master_inputs.json is a copy followed by the hand-written inputs of purely dynamic models

With --update, rewrite the resources from the Nordic example instead, keeping those hand-written inputs.
"""

import argparse
import json
import sys
from pathlib import Path

RESOURCES = Path(__file__).parent
NORDIC = RESOURCES.parent.parent.parent.parent / "docs" / "orchestrator" / "examples" / "Nordic"

COPIES = {  # resource -> Nordic file
    "Nordic.xiidm": "Nordic.xiidm",
    "game_master_outputs.json": "game_master_outputs.json",
}
INPUTS, NORDIC_INPUTS = "game_master_inputs.json", "game_master_inputs.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_hand_written(entry):
    """The inputs appended by hand: purely dynamic models"""
    return entry.get("equipmentId") is None and "model" in entry and "model_lib" in entry


def check():
    ok = True
    for resource, nordic in COPIES.items():
        if (RESOURCES / resource).read_bytes() != (NORDIC / nordic).read_bytes():
            print(f"❌ {resource} differs from {NORDIC / nordic}")
            ok = False

    inputs, nordic_inputs = load_json(RESOURCES / INPUTS), load_json(NORDIC / NORDIC_INPUTS)
    copied, appended = inputs[:len(nordic_inputs)], inputs[len(nordic_inputs):]
    if copied != nordic_inputs:
        print(f"❌ {INPUTS} does not start with the entries of {NORDIC / NORDIC_INPUTS}")
        ok = False
    if not all(is_hand_written(entry) for entry in appended):
        print(f"❌ {INPUTS} should only add hand-written inputs of purely dynamic models to the Nordic ones (see README.md)")
        ok = False
    return ok


def update():
    for resource, nordic in COPIES.items():
        (RESOURCES / resource).write_bytes((NORDIC / nordic).read_bytes())
    nordic_inputs = load_json(NORDIC / NORDIC_INPUTS)
    # Skip the ones the configurator now generates itself
    generated_ids = {entry["id"] for entry in nordic_inputs}
    hand_written = [entry for entry in load_json(RESOURCES / INPUTS) if is_hand_written(entry) and entry["id"] not in generated_ids]
    with open(RESOURCES / INPUTS, "w", encoding="utf-8") as f:
        json.dump(nordic_inputs + hand_written, f, indent=4)
    print(f"Updated the resources from {NORDIC}, keeping {len(hand_written)} hand-written inputs")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[-1], formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true", help="Rewrite the resources from the Nordic example")
    if parser.parse_args().update:
        update()
    elif check():
        print("✅ DSL test resources match the Nordic example")
    else:
        print("Run ./cfg.sh in the Nordic example, then this script with --update, and re-run the DSL tests")
        sys.exit(1)
