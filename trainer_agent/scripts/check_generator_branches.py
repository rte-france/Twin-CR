"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

List generators whose bus is connected to the rest of the network through more than N branches.

Usage: python check_generator_branches.py [network_file] [max_branches]
"""

import sys
from collections import Counter

import pypowsybl.network as pn

path = sys.argv[1] if len(sys.argv) > 1 else "temp copy.xiidm"
max_branches = int(sys.argv[2]) if len(sys.argv) > 2 else 2

net = pn.load(path)

# Count branches (lines + 2-winding transformers) per bus (bus view, merged buses)
branch_count = Counter()
for df in (net.get_lines(), net.get_2_windings_transformers()):
    for col in ("bus1_id", "bus2_id"):
        branch_count.update(b for b in df[col] if b)
# 3-winding transformers count as branches on each of their legs
t3 = net.get_3_windings_transformers()
for col in ("bus1_id", "bus2_id", "bus3_id"):
    if col in t3:
        branch_count.update(b for b in t3[col] if b)

gens = net.get_generators()
gens["n_branches"] = gens["bus_id"].map(lambda b: branch_count.get(b, 0))
res = gens[gens["n_branches"] > max_branches]

print(f"{len(gens)} generators, {len(res)} on a bus with more than {max_branches} branches")
if len(res):
    print(res[["voltage_level_id", "bus_id", "max_p", "target_p", "connected", "n_branches"]].to_string())

# Significant units (max_p above threshold)
min_pmax = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0
big = res[res["max_p"] > min_pmax]
print(f"\n{len(big)} of them have max_p > {min_pmax} MW")
if len(big):
    print(big[["voltage_level_id", "bus_id", "max_p", "target_p", "n_branches"]].to_string())
