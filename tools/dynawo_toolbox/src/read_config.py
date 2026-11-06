"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

"""
Print one value from a config.toml, so shell scripts can read it without a TOML
parser of their own. Keeps main_configure itself independent of config.toml.

    read_config.py config.toml input_files.job_file
    read_config.py config.toml input_files.extra_io_file --optional  # Prints nothing if the key is absent
"""

import sys
import tomllib


def main(config_path: str, dotted_key: str, optional: bool = False) -> int:
    with open(config_path, "rb") as config_file:
        value = tomllib.load(config_file)

    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            if optional:
                return 0
            print(f"{config_path}: no such key {dotted_key}", file=sys.stderr)
            return 1
        value = value[part]

    print(value)
    return 0


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if arg != "--optional"]
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(args[0], args[1], optional="--optional" in sys.argv[1:]))
