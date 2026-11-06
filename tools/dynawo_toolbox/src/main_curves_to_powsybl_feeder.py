"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import argparse
import json

SIDE={"ONE": "1", "TWO": "2"}
VAR={"ARROW_ACTIVE": "P", "ARROW_REACTIVE": "Q", "ARROW_CURRENT": "i"}

def feeder_to_curve(feeder):
    if "componentType" not in feeder or feeder["componentType"] not in VAR.keys():
        return None
    side = SIDE[feeder["side"]] if "side" in feeder else ""
    var = VAR[feeder["componentType"]]
    return f'{feeder["equipmentId"]}_{var}{side}_value'

def main(metadata_file, output_file):
    with open(metadata_file) as f:
        data = json.load(f)
        feeders = data["metadata"]["feederInfos"]
        print(feeders)
        for feeder in feeders:
            feeder["dynawo_id"] = feeder_to_curve(feeder)
            print(feeder["dynawoId"])
        with open(output_file, 'w') as o_f:
            o_f.write(feeders)

def parse_args():
    parser = argparse.ArgumentParser(description="Populate feeder metadata configuration with default curve name")
    parser.add_argument('--metadata_file', '-m', type=str, required=True, help='metadata file')
    parser.add_argument('--output_file', '-o', type=str, required=True, help='output file')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    main(args.metadata_file, args.output_file)
