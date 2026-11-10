"""
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Helpers to build synoptic definitions (see tools/synoptic/README.md).

The network is read with pypowsybl (any format / compression powsybl supports) into small dataclasses, so that the
generators (here and e.g. converters of existing SCADA pictures) only depend on the few fields they use.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

FORMAT = "twincr-synoptic/1"


# --------------------------------------------------------------------------------------------
# Minimal network structure dataclasses needed by synoptic
# --------------------------------------------------------------------------------------------

@dataclass
class VoltageLevel:
    id: str
    substation: str
    nominal_v: float
    name: str | None = None


@dataclass
class Branch:
    id: str
    kind: str  # line | twt | tieLine | hvdc
    vl1: str
    vl2: str


@dataclass
class Generator:
    id: str
    vl: str
    name: str | None = None


@dataclass
class Network:
    substations: dict[str, dict] = field(default_factory=dict)  # id -> {country, name, lon, lat}
    voltage_levels: dict[str, VoltageLevel] = field(default_factory=dict)
    branches: dict[str, Branch] = field(default_factory=dict)
    generators: dict[str, Generator] = field(default_factory=dict)

    def substation_of(self, vl_id: str) -> str:
        vl = self.voltage_levels.get(vl_id)
        return vl.substation if vl else ""


def _name(value) -> str | None:
    return value if isinstance(value, str) and value else None


def read_iidm(path: str | Path) -> Network:
    """Read the static structure of a network file (substations, voltage levels, branches, generators).
    Three windings transformers are not read (a branch has two sides)."""
    import pypowsybl as pp  # Imported here: starting its JVM is only needed when a network is read

    n = pp.network.load(str(path))
    net = Network()
    for sid, row in n.get_substations(attributes=["name", "country"]).iterrows():
        net.substations[str(sid)] = {"country": _name(row["country"]), "name": _name(row["name"])}
    positions = n.get_extensions("substationPosition")
    for sid, row in positions.iterrows():
        if sid in net.substations:
            net.substations[sid]["lon"] = float(row["longitude"])
            net.substations[sid]["lat"] = float(row["latitude"])
    for vid, row in n.get_voltage_levels(attributes=["name", "substation_id", "nominal_v"]).iterrows():
        net.voltage_levels[str(vid)] = VoltageLevel(str(vid), str(row["substation_id"]), float(row["nominal_v"]), _name(row["name"]))

    sides = ["voltage_level1_id", "voltage_level2_id"]
    for kind, df in (("line", n.get_lines(attributes=sides)), ("twt", n.get_2_windings_transformers(attributes=sides))):
        for bid, row in df.iterrows():
            net.branches[str(bid)] = Branch(str(bid), kind, str(row["voltage_level1_id"]), str(row["voltage_level2_id"]))
    dangling_vl = n.get_dangling_lines(attributes=["voltage_level_id"])["voltage_level_id"].to_dict()
    for bid, row in n.get_tie_lines(attributes=["dangling_line1_id", "dangling_line2_id"]).iterrows():
        vl1, vl2 = dangling_vl.get(row["dangling_line1_id"]), dangling_vl.get(row["dangling_line2_id"])
        if vl1 and vl2:
            net.branches[str(bid)] = Branch(str(bid), "tieLine", vl1, vl2)
    converter_vl = {**n.get_vsc_converter_stations(attributes=["voltage_level_id"])["voltage_level_id"].to_dict(),
                    **n.get_lcc_converter_stations(attributes=["voltage_level_id"])["voltage_level_id"].to_dict()}
    for bid, row in n.get_hvdc_lines(attributes=["converter_station1_id", "converter_station2_id"]).iterrows():
        vl1, vl2 = converter_vl.get(row["converter_station1_id"]), converter_vl.get(row["converter_station2_id"])
        if vl1 and vl2:
            net.branches[str(bid)] = Branch(str(bid), "hvdc", vl1, vl2)

    gens = n.get_generators(attributes=["name", "voltage_level_id"])
    for gid, row in gens.iterrows():
        net.generators[str(gid)] = Generator(str(gid), str(row["voltage_level_id"]), _name(row["name"]))
    return net


def output_ids_by_kind(outputs_file: str | Path | None) -> dict[str, list[str]]:
    """kind -> ids of a game_master_outputs.json / scada_outputs.json, e.g. "OmegaRef" -> ["OMEGA_REF_omegaRef_0_value"]
    (the ids of the outputs without equipment depend on the Dynawo model names of the case)."""
    if not outputs_file:
        return {}
    result: dict[str, list[str]] = {}
    for o in json.loads(Path(outputs_file).read_text(encoding="utf-8")):
        if o.get("kind") and o.get("id"):
            result.setdefault(o["kind"], []).append(o["id"])
    return result


def resolve_output_placeholders(value, outputs: dict[str, list[str]]):
    """Replace the expressions "{out:<kind>}" by out('<first output id of this kind>'), None if there is none."""
    if isinstance(value, dict):
        return {k: resolve_output_placeholders(v, outputs) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_output_placeholders(v, outputs) for v in value]
    if isinstance(value, str) and "{out:" in value:
        missing = False

        def sub(m):
            nonlocal missing
            ids = outputs.get(m.group(1))
            if not ids:
                missing = True
                return "nan()"
            return f"out({q(ids[0])})"
        result = re.sub(r"\{out:([^}]+)\}", sub, value)
        return None if missing else result
    return value


# --------------------------------------------------------------------------------------------
# Expressions
# --------------------------------------------------------------------------------------------

def q(identifier: str) -> str:
    """Quote an id for an expression."""
    if "'" not in identifier:
        return f"'{identifier}'"
    if '"' in identifier:
        raise ValueError(f"id {identifier!r} contains both quote kinds")
    return f'"{identifier}"'


def loading_expr(branch_id: str, scale: float = 10, rounding: bool = True) -> str:
    """Current loading of a branch: scale = 10 gives deciles of the permanent limit, 100 gives %."""
    b = q(branch_id)
    s1 = f"abs(i1({b}))/ilim1({b})"
    s2 = f"abs(i2({b}))/ilim2({b})"
    inner = f"{scale:g}*coalesce(max({s1}, {s2}), {s1}, {s2})"
    return f"round({inner})" if rounding else inner


def flow_dir_expr(branch_id: str) -> str:
    """Positive when the active power flows from side 1 to side 2."""
    b = q(branch_id)
    return f"coalesce(p1({b}), -p2({b}))"


def unit_on_expr(gen_id: str, min_mw: float = 1.0) -> str:
    g = q(gen_id)
    return f"connected({g}) && pgen({g}) > {min_mw:g}"


# --------------------------------------------------------------------------------------------
# Geometry and element builders
# --------------------------------------------------------------------------------------------

def rnd(v: float) -> float:
    return round(v, 1)


def segment_between(p1, r1, p2, r2, offset=0.0):
    """Straight segment between the borders of two circles, shifted perpendicularly by offset."""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    d = math.hypot(dx, dy) or 1.0
    ux, uy = dx / d, dy / d
    nx, ny = -uy, ux
    # Start on the circle border, at the shifted position
    def border(x, y, r, sign):
        o = max(min(offset, r * 0.9), -r * 0.9)
        along = math.sqrt(max(r * r - o * o, 0.0))
        return x + sign * ux * along + nx * o, y + sign * uy * along + ny * o
    a = border(x1, y1, r1, 1)
    b = border(x2, y2, r2, -1)
    return [[rnd(a[0]), rnd(a[1])], [rnd(b[0]), rnd(b[1])]]


def parallel_offsets(n: int, spacing: float) -> list[float]:
    return [(i - (n - 1) / 2) * spacing for i in range(n)]


def point_along(points, t: float):
    """Point at fraction t of a polyline length, and the direction angle (degrees) there."""
    lengths = [math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1]) for i in range(len(points) - 1)]
    total = sum(lengths) or 1.0
    target = t * total
    acc = 0.0
    for i, seg in enumerate(lengths):
        if acc + seg >= target or i == len(lengths) - 1:
            u = 0.0 if seg == 0 else (target - acc) / seg
            (x1, y1), (x2, y2) = points[i], points[i + 1]
            return (x1 + u * (x2 - x1), y1 + u * (y2 - y1)), math.degrees(math.atan2(y2 - y1, x2 - x1))
        acc += seg
    return tuple(points[-1]), 0.0


def branch_element(branch_id: str, points, side1: int = 1, width: float = 2, **extra) -> dict:
    e = {"type": "branch", "branch": branch_id, "points": points, "width": width}
    if side1 != 1:
        e["side1"] = side1
    e.update(extra)
    return e


def flow_arrow_element(branch_id: str, points, side1: int = 1, t: float = 0.5, size: float = 16,
                       label_distance: float = 14, scale: float = 10, fmt: str = "%.0f", suffix: str = "",
                       label_side: int = 1) -> dict:
    """Arrow on a branch, pointing in the direction of the active power, labelled with its loading."""
    (x, y), angle = point_along(points, t)
    if side1 == 2:
        angle += 180  # points are drawn from network side 2 to side 1
    rad = math.radians(angle - 90 * label_side * (-1 if side1 == 2 else 1))
    e = {
        "type": "arrow", "x": rnd(x), "y": rnd(y), "angle": rnd(angle), "size": size,
        "dir": flow_dir_expr(branch_id), "deadband": 0.5,
        "expr": loading_expr(branch_id, scale), "format": fmt,
        "labelDx": rnd(math.cos(rad) * label_distance), "labelDy": rnd(math.sin(rad) * label_distance),
        "thresholds": [{"value": 0.9 * scale, "fill": "#ffb000"}, {"value": scale, "fill": "#ff3030"}],
        "equipment": branch_id,
    }
    if suffix:
        e["suffix"] = suffix
    return e


def node_element(vl_id: str, x: float, y: float, r: float, **extra) -> dict:
    e = {"type": "node", "vl": vl_id, "x": rnd(x), "y": rnd(y), "r": r}
    e.update(extra)
    return e


def text_element(text: str, x: float, y: float, **extra) -> dict:
    e = {"type": "text", "text": text, "x": rnd(x), "y": rnd(y)}
    e.update(extra)
    return e


def value_element(expr: str | None, x: float, y: float, fmt: str = "%.0f", **extra) -> dict:
    """Displayed as "?" when expr is None or cannot be evaluated."""
    e = {"type": "value", "expr": expr, "x": rnd(x), "y": rnd(y), "format": fmt}
    e.update(extra)
    return e


def unit_element(on_expr: str | None, x: float, y: float, r: float, label: str = "", equipment: str | None = None,
                 **extra) -> dict:
    """Generating unit; "equipment" (generator id) feeds the argus context menu / properties"""
    e = {"type": "unit", "on": on_expr, "x": rnd(x), "y": rnd(y), "r": r, "label": label}
    if equipment:
        e["equipment"] = equipment
    e.update(extra)
    return e


def table_element(x: float, y: float, rows: list[dict], **extra) -> dict:
    """rows: [{"label": ..., "expr": ... | None, "format": ..., "suffix": ...} | {"label": ..., "text": ...}]"""
    e = {"type": "table", "x": rnd(x), "y": rnd(y), "rows": rows}
    e.update(extra)
    return e


def synoptic(name: str, title: str, width: float, height: float, elements: list[dict], **extra) -> dict:
    d = {"format": FORMAT, "name": name, "title": title, "width": width, "height": height,
         "background": "#1c3f41"}
    d.update(extra)
    d["elements"] = elements
    return d


def dumps(definition: dict) -> str:
    """JSON with one element per line (readable diffs, reasonable size)."""
    head = {k: v for k, v in definition.items() if k != "elements"}
    lines = [json.dumps(head, indent=1, ensure_ascii=False)[:-2] + ',\n "elements": [']
    elements = definition.get("elements", [])
    for i, e in enumerate(elements):
        lines.append("  " + json.dumps(e, ensure_ascii=False) + ("," if i < len(elements) - 1 else ""))
    lines.append(" ]\n}\n")
    return "\n".join(lines)


def write_synoptic(definition: dict, out_dir: str | Path) -> Path:
    """Write <out_dir>/<name>.json and register it in <out_dir>/index.json."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{definition['name']}.json"
    path.write_text(dumps(definition), encoding="utf-8")
    index_path = out / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else []
    if path.name not in index:
        index.append(path.name)
    index_path.write_text(json.dumps(index, indent=1) + "\n")
    return path
