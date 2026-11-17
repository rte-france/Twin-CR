"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.

Add the dynamic parameter governor_KGover (from the .par file) to the pypowsybl generators table.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import pypowsybl as ps

DYNAWO_NS = "{http://www.rte-france.com/dynawo}"


def read_par_values(par_file, par_name):
    """Return {set_id: float value} for the parameter `par_name` in a Dynawo .par file."""
    values = {}
    for _, elem in ET.iterparse(par_file):
        if elem.tag == f"{DYNAWO_NS}set":
            for par in elem.iterfind(f"{DYNAWO_NS}par"):
                if par.get("name") == par_name:
                    values[elem.get("id")] = float(par.get("value"))
            elem.clear()
    return values


def read_static_to_par_id(dyd_file, par_file_name):
    """Return {staticId: parId} for the black box models of the .dyd file that use `par_file_name`."""
    mapping = {}
    root = ET.parse(dyd_file).getroot()
    for bbm in root.iterfind(f"{DYNAWO_NS}blackBoxModel"):
        static_id, par_id = bbm.get("staticId"), bbm.get("parId")
        if static_id and par_id and Path(bbm.get("parFile", "")).name == par_file_name:
            mapping[static_id] = par_id
    return mapping


def read_governor_kgover(gen_ids, par_file, dyd_file=None, par_name="governor_KGover"):
    """Return a float Series (indexed like network.get_generators()) of the `par_name` dynamic parameter.

    Each generator is linked to its parameter set through the .dyd file (staticId -> parId).
    Generators without a dynamic model or whose set has no `par_name` get NaN.
    """
    par_file = Path(par_file)
    dyd_file = Path(dyd_file) if dyd_file else par_file.with_suffix(".dyd")

    values_by_set = read_par_values(par_file, par_name)
    par_id_by_static = read_static_to_par_id(dyd_file, par_file.name)

    values = [values_by_set.get(par_id_by_static.get(gen_id)) for gen_id in gen_ids]
    return pd.Series(values, index=gen_ids, name=par_name, dtype=float)


def get_generators_with_governor_kgover(network, par_file, dyd_file=None, par_name="governor_KGover"):
    """Return network.get_generators() with an extra `par_name` column (see read_governor_kgover)."""
    generators = network.get_generators()
    generators[par_name] = read_governor_kgover(generators.index, par_file, dyd_file, par_name)
    return generators


if __name__ == "__main__":
    import os
    
    iidm_file = Path(os.getenv("IIDM_FILE"))
    net = ps.network.load(str(iidm_file))
    gens = get_generators_with_governor_kgover(net, iidm_file.with_suffix(".par"), iidm_file.with_suffix(".dyd"))
    print(gens[["governor_KGover"]].describe())
    print(gens[["governor_KGover"]].head())
