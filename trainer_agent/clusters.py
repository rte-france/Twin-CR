"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import colorcet as cc
import json
import os
import pandas as pd
import pypowsybl as ps
import sklearn


def load_coordinates():

    with open(os.getenv("COORDINATES_FILE")) as f:
        substations = json.load(f)["features"]

    coordinates = []
    for substation in substations:
        code = substation["properties"]["code_poste"]
        coordinates.append([code] + substation["geometry"]["coordinates"])

    return coordinates

def get_clusters(n_clusters=100):
    coordinates = load_coordinates()
    coordinates = pd.DataFrame(coordinates, columns = ["substation_id", "x", "y"])
    coordinates = coordinates.drop_duplicates(subset="substation_id")
    kmeans = sklearn.cluster.KMeans(n_clusters, random_state=0).fit(coordinates[["x", "y"]])
    coordinates["group"] = [str(x) for x in kmeans.labels_]

    return coordinates

def add_coordinates_to_network(net):
    coordinates = load_coordinates()
    coordinates = pd.DataFrame(coordinates, columns = ["id", "longitude", "latitude"])
    coordinates = coordinates.set_index("id")
    substations = net.get_substations()

    manual_coordinates = substations[substations["country"] == "BE"]
    manual_coordinates["latitude"] = 50.85
    manual_coordinates["longitude"] = 4.35
    coordinates = pd.concat([coordinates, manual_coordinates[["latitude", "longitude"]]])
    
    manual_coordinates = substations[substations["country"] == "CH"]
    manual_coordinates["latitude"] = 47
    manual_coordinates["longitude"] = 8
    coordinates = pd.concat([coordinates, manual_coordinates[["latitude", "longitude"]]])

    manual_coordinates = substations[substations["country"] == "DE"]
    manual_coordinates["latitude"] = 50#51
    manual_coordinates["longitude"] = 8.7#10
    coordinates = pd.concat([coordinates, manual_coordinates[["latitude", "longitude"]]])

    manual_coordinates = substations[substations["country"] == "NL"]
    manual_coordinates["latitude"] = 52
    manual_coordinates["longitude"] = 5
    coordinates = pd.concat([coordinates, manual_coordinates[["latitude", "longitude"]]])

    manual_coordinates = substations[substations["country"] == "GB"]
    manual_coordinates["latitude"] = 51#54
    manual_coordinates["longitude"] = 0#2.5
    coordinates = pd.concat([coordinates, manual_coordinates[["latitude", "longitude"]]])

    manual_coordinates = substations[substations["country"] == "ES"]
    manual_coordinates["latitude"] = 41.5#40
    manual_coordinates["longitude"] = -0.4#4
    coordinates = pd.concat([coordinates, manual_coordinates[["latitude", "longitude"]]])

    manual_coordinates = substations[substations["country"] == "IT"]
    manual_coordinates["latitude"] = 45#41
    manual_coordinates["longitude"] = 9.2#12
    coordinates = pd.concat([coordinates, manual_coordinates[["latitude", "longitude"]]])

    manual_coordinates = substations[substations["country"] == "LU"]
    manual_coordinates["latitude"] = 49.75
    manual_coordinates["longitude"] = 6.17
    coordinates = pd.concat([coordinates, manual_coordinates[["latitude", "longitude"]]])

    index = list(set(substations.index) & set(coordinates.index))
    coordinates = coordinates.loc[index]
    net.create_extensions("substationPosition", coordinates)
    parameter = ps.network.NadParameters(layout_type=ps.network.NadLayoutType.GEOGRAPHICAL)
    net.write_network_area_diagram("network.svg", low_nominal_voltage_bound=200, nad_parameters=parameter)

if __name__ == "__main__":
    net = ps.network.load(os.getenv("IIDM_FILE"))
    add_coordinates_to_network(net)
    from matplotlib import pyplot as plt

    coordinates = get_clusters()
    for i, (cat, df) in enumerate(coordinates.groupby('group')):
        plt.scatter(df['x'], df['y'], label=cat, color=cc.glasbey_bw[i])

    plt.show()