"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import pandas as pd
from pathlib import Path
from tqdm import tqdm

folder = Path("/Users/martin/data_grid2op/")
dataset = "l2rpn_wcci_2020"
infos = []
for chronic in tqdm(list((folder / dataset / "chronics").glob("*"))):
    if chronic.is_dir():
        load_p = pd.read_csv(chronic / "load_p.csv.bz2", sep=";")
        total_load = load_p.sum(axis=1)
        prod_p = pd.read_csv(chronic / "prod_p.csv.bz2", sep=";")
        total_prod = prod_p.sum(axis=1)

        info = pd.DataFrame([total_load, total_prod]).transpose()
        
        info = info.set_axis(['load', 'prod'], axis=1)
        info["chronic"] = chronic.name

        infos.append(info)


infos = pd.concat(infos)
infos.to_csv("infos.csv")
print()