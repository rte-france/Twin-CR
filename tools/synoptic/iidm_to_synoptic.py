"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Generate a synoptic definition (argus "Synoptic" window) from a network file (any format powsybl reads).

Substations are placed with their geographical position (substationPosition extension) when every
displayed substation has one, otherwise with a deterministic force-directed layout.

Example (Nordic):
    uv run --project tools/synoptic python tools/synoptic/iidm_to_synoptic.py docs/orchestrator/examples/Nordic/Nordic.xiidm \\
        --outputs docs/orchestrator/examples/Nordic/game_master_outputs.json \\
        --out docs/orchestrator/examples/Nordic/synoptics --name nordic --title "Nordic 32"
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import synoptic_lib as L  # noqa: E402


def force_layout(nodes: list[str], edges: list[tuple[str, str]], iterations: int = 600, seed: int = 0) -> dict[str, tuple[float, float]]:
    """Fruchterman-Reingold layout in the unit square (deterministic)."""
    rng = random.Random(seed)
    pos = {n: [rng.random(), rng.random()] for n in nodes}
    if len(nodes) < 2:
        return {n: (0.5, 0.5) for n in nodes}
    k = math.sqrt(1.0 / len(nodes))
    temperature = 0.1
    for it in range(iterations):
        disp = {n: [0.0, 0.0] for n in nodes}
        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = max(math.hypot(dx, dy), 1e-4)
                f = k * k / d
                disp[a][0] += dx / d * f
                disp[a][1] += dy / d * f
                disp[b][0] -= dx / d * f
                disp[b][1] -= dy / d * f
        for a, b in edges:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = max(math.hypot(dx, dy), 1e-4)
            f = d * d / k
            disp[a][0] -= dx / d * f
            disp[a][1] -= dy / d * f
            disp[b][0] += dx / d * f
            disp[b][1] += dy / d * f
        for n in nodes:
            dx, dy = disp[n]
            d = max(math.hypot(dx, dy), 1e-9)
            step = min(d, temperature)
            pos[n][0] += dx / d * step
            pos[n][1] += dy / d * step
        temperature = max(0.1 * (1 - it / iterations), 0.002)
    return {n: (p[0], p[1]) for n, p in pos.items()}


def fit(points: dict[str, tuple[float, float]], width: float, height: float, margin: float, flip_y: bool) -> dict[str, tuple[float, float]]:
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    sx = (width - 2 * margin) / max(x1 - x0, 1e-9)
    sy = (height - 2 * margin) / max(y1 - y0, 1e-9)
    out = {}
    for n, (x, y) in points.items():
        px = margin + (x - x0) * sx
        py = margin + ((y1 - y) if flip_y else (y - y0)) * sy
        out[n] = (px, py)
    return out


def build(net: L.Network, name: str, title: str, min_kv: float, width: float, height: float,
          outputs: dict[str, list[str]] | None = None) -> dict:
    shown_vls = {v.id for v in net.voltage_levels.values() if v.nominal_v >= min_kv}
    branches = [b for b in net.branches.values() if b.vl1 in shown_vls and b.vl2 in shown_vls]
    connected_vls = {b.vl1 for b in branches} | {b.vl2 for b in branches}
    shown_vls &= connected_vls
    subs = sorted({net.voltage_levels[v].substation for v in shown_vls})

    # Substation positions
    geo = all("lon" in net.substations.get(s, {}) for s in subs)
    if geo:
        raw = {s: (net.substations[s]["lon"], net.substations[s]["lat"]) for s in subs}
    else:
        edges = sorted({tuple(sorted((net.substation_of(b.vl1), net.substation_of(b.vl2))))
                        for b in branches if net.substation_of(b.vl1) != net.substation_of(b.vl2)})
        raw = force_layout(subs, edges)  # type: ignore[arg-type]
    sub_pos = fit(raw, width, height, margin=90, flip_y=geo)

    # Voltage levels of a substation side by side, highest voltage first
    vl_pos: dict[str, tuple[float, float]] = {}
    vl_r: dict[str, float] = {}
    max_kv = max(net.voltage_levels[v].nominal_v for v in shown_vls)
    by_sub = defaultdict(list)
    for v in shown_vls:
        by_sub[net.voltage_levels[v].substation].append(v)
    for s, vls in by_sub.items():
        vls.sort(key=lambda v: (-net.voltage_levels[v].nominal_v, v))
        x, y = sub_pos[s]
        for i, v in enumerate(vls):
            vl_pos[v] = (x + i * 62, y + i * 34)  # Lower voltages below right
            vl_r[v] = 16 if net.voltage_levels[v].nominal_v >= max_kv else 11

    elements: list[dict] = [L.text_element(title, 20, 24, anchor="start", fontSize=22, bold=True, fill="#ffff40")]

    # Branches, parallel circuits side by side
    groups = defaultdict(list)
    for b in sorted(branches, key=lambda b: b.id):
        if b.vl1 == b.vl2:
            continue
        groups[tuple(sorted((b.vl1, b.vl2)))].append(b)
    arrows = []
    for (va, vb), group in groups.items():
        for i, (b, off) in enumerate(zip(group, L.parallel_offsets(len(group), 8))):
            pts = L.segment_between(vl_pos[va], vl_r[va], vl_pos[vb], vl_r[vb], off)
            side1 = 1 if b.vl1 == va else 2
            elements.append(L.branch_element(b.id, pts, side1=side1, width=2))
            if b.kind != "twt" and math.dist(*pts) > 60:
                # Parallel circuits: staggered arrows, labels on the outer side
                t = 0.5 + (i - (len(group) - 1) / 2) * 0.18
                arrows.append(L.flow_arrow_element(b.id, pts, side1=side1, t=t, size=14, label_distance=13,
                                                   label_side=-1 if off < 0 else 1))
    elements.extend(arrows)

    # Voltage levels: circle, name, voltage
    for v in sorted(shown_vls):
        x, y = vl_pos[v]
        r = vl_r[v]
        vl = net.voltage_levels[v]
        elements.append(L.node_element(v, x, y, r))
        elements.append(L.text_element(vl.name or v, x, y - r - 18, fontSize=12))
        elements.append(L.value_element(f"v({L.q(v)})", x, y - r - 5, fontSize=11, suffix=" kV"))

    # Generating units: row of small circles under the highest voltage level of their substation
    gens_by_sub = defaultdict(list)
    for g in net.generators.values():
        s = net.substation_of(g.vl)
        if s in by_sub:
            gens_by_sub[s].append(g)
    for s, gens in gens_by_sub.items():
        anchor = by_sub[s][0]
        x, y = vl_pos[anchor]
        gens.sort(key=lambda g: g.id)
        for i, g in enumerate(gens):
            gx = x + (i - (len(gens) - 1) / 2) * 22
            elements.append(L.unit_element(L.unit_on_expr(g.id), gx, y + vl_r[anchor] + 18, 9, label=str(i + 1),
                                           equipment=g.id))

    # Summary table
    gen_ids = sorted(net.generators)
    if gen_ids:
        total = "sum(" + ", ".join(f"coalesce(pgen({L.q(g)}), 0)" for g in gen_ids) + ")"
        units_on = "sum(" + ", ".join(f"coalesce({L.unit_on_expr(g)}, 0)" for g in gen_ids) + ")"
        rows = [
            {"label": "Total generation", "expr": total, "format": "%.0f", "suffix": " MW"},
            {"label": "Units in operation", "expr": units_on, "format": "%.0f", "suffix": f" / {len(gen_ids)}"},
        ]
        frequency = L.resolve_output_placeholders("{out:OmegaRef}", outputs or {})
        if frequency:
            rows.insert(0, {"label": "Frequency", "expr": frequency, "format": "%.3f", "suffix": " Hz"})
        elements.append(L.table_element(width - 330, height - 30 - 30 * len(rows), rows,
                                        labelWidth=200, valueWidth=110, fill="#163234"))

    return L.synoptic(name, title, width, height, elements)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("iidm", help="network file (XIIDM, possibly compressed, or any format powsybl reads)")
    parser.add_argument("--out", required=True, help="synoptics directory ([input_files.argus] synoptics_dir)")
    parser.add_argument("--name", required=True, help="synoptic name (file <name>.json)")
    parser.add_argument("--title", default=None)
    parser.add_argument("--min-kv", type=float, default=100, help="lowest nominal voltage displayed")
    parser.add_argument("--width", type=float, default=1800)
    parser.add_argument("--height", type=float, default=1200)
    parser.add_argument("--outputs", help="game_master_outputs.json, to display the outputs without equipment (frequency)")
    args = parser.parse_args()

    net = L.read_iidm(args.iidm)
    definition = build(net, args.name, args.title or args.name, args.min_kv, args.width, args.height,
                       L.output_ids_by_kind(args.outputs))
    path = L.write_synoptic(definition, args.out)
    print(f"Wrote {path} ({len(definition['elements'])} elements)")


if __name__ == "__main__":
    main()
