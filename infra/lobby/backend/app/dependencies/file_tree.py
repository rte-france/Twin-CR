"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

from collections.abc import Mapping, Sequence
from typing import Any

NodeRow = Mapping[Any, Any]


FileNode = dict[str, Any]


def build_file_tree(
    rows: Sequence[NodeRow],
) -> tuple[dict[str, FileNode], list[FileNode]]:
    nodes: dict[str, FileNode] = {
        row["id"]: {
            "id": row["id"],
            "name": row["name"],
            "is_directory": row["is_directory"],
            "s3_object_key": row["s3_object_key"],
            "children": [],
        }
        for row in rows
    }

    roots: list[FileNode] = []
    for row in rows:
        parent_id = row["parent_id"]
        if parent_id and parent_id in nodes and parent_id != row["id"]:
            nodes[parent_id]["children"].append(nodes[row["id"]])
        else:
            roots.append(nodes[row["id"]])

    return nodes, roots
