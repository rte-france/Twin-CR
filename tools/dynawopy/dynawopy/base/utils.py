"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""


from collections import deque

def bfs_nearest(start_node, graph, blocked_node=None, target_node_map=None):
    """
    BFS over node-breaker graph.
    Returns the nearest target element whose node is reached first.
    """
    if target_node_map is None:
        target_node_map = {}

    visited = set()
    queue = deque([start_node])

    if blocked_node is not None:
        visited.add(blocked_node)

    visited.add(start_node)

    # If start node itself is already a target
    if start_node in target_node_map:
        return target_node_map[start_node]

    while queue:
        current = queue.popleft()

        for neighbor in graph[current]:
            if neighbor in visited:
                continue

            visited.add(neighbor)

            if neighbor in target_node_map:
                return target_node_map[neighbor]

            queue.append(neighbor)

    return None
