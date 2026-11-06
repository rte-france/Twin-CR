"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
import lzma
from pathlib import Path
from typing import Any

import zstandard


def load_json(path: str | Path) -> Any:
    """Read a JSON file that may be xz or zstd compressed.

    The backends accept the mapping files in any of these forms (see FileLoader), so the tooling
    has to as well: which one a scenario ships is a trade between repository size and load time.
    """
    name = str(path).lower()
    if name.endswith(".xz"):
        with lzma.open(path) as stream:
            return json.load(stream)
    if name.endswith(".zst"):
        with open(path, "rb") as compressed:
            with zstandard.ZstdDecompressor().stream_reader(compressed) as stream:
                return json.load(stream)
    with open(path, "rb") as stream:
        return json.load(stream)
