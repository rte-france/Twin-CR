"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
import networkx as nx

class CyberConfigParser:
    def __init__(self):
        pass

    @staticmethod
    def parse_config(cyber_config_file) -> nx.DiGraph:
        graph = nx.DiGraph()
        with open(cyber_config_file, 'r') as f:
            config_data = json.load(f)

        # Parse nodes
        nodes = config_data.get("nodes", [])
        for node in nodes:
            xpos = node.get("xpos", None)
            ypos = node.get("ypos", None)
            if xpos and ypos:
                graph.add_node(node["node"], pos=(xpos, ypos))
            else:
                graph.add_node(node["node"])

        # Parse nodes from links
        # links = config_data.get("links", [])
        # for link in links:
        #     if link['from'] in graph.nodes and graph.nodes[link['from']]['type'] != link['fromtype']:
        #         raise ValueError(f"Node {link['from']} already exists with a different type.")
        #     if link['to'] in graph.nodes and graph.nodes[link['to']]['type'] != link['totype']:
        #         raise ValueError(f"Node {link['to']} already exists with a different type.")
        #     graph.add_node(link['from'], type=link['fromtype'])
        #     graph.add_node(link['to'], type=link['totype'])

        # # Parse node characteristics by node types
        # if 'nodes_characteristics_by_type' in config_data:
        #     for characteristic in config_data['nodes_characteristics_by_type']:
        #         nodetype = characteristic['type']
        #         delay = characteristic.get('delay', {})
        #         drop = characteristic.get('drop', {})
        #         corruption = characteristic.get('corruption', {})
        #         for u, data in graph.nodes(data=True):
        #             if data['type'] == nodetype:
        #                 data['characteristics'] = {
        #                     'delay': delay,
        #                     'drop': drop,
        #                     'corruption': corruption
        #                 }

        # # Parse node characteristics
        # characteristics_by_nodes = config_data.get("nodes_characteristics", [])
        # for characteristic in characteristics_by_nodes:
        #     u = characteristic['node']
        #     delay = characteristic.get('delay', {})
        #     drop = characteristic.get('drop', {})
        #     corruption = characteristic.get('corruption', {})
        #     if u in graph.nodes:
        #         graph.nodes[u]['characteristics'] = {
        #             'delay': delay,
        #             'drop': drop,
        #             'corruption': corruption
        #         }

        # Parse links
        links = config_data.get("links", [])
        for link in links:
            if not graph.has_node(link['from']) or not graph.has_node(link['to']):
                continue
            graph.add_edge(link['from'], link['to'], fromtype=link['fromtype'], totype=link['totype'])

        # # Parse links characteristics by link type
        # characteristics_by_type = config_data.get("links_characteristics_by_link_type", [])
        # for characteristic in characteristics_by_type:
        #     fromtype = characteristic['fromtype']
        #     totype = characteristic['totype']
        #     delay = characteristic.get('delay', {})
        #     drop = characteristic.get('drop', {})
        #     corruption = characteristic.get('corruption', {})
        #     for u, v, data in graph.edges(data=True):
        #         if data['fromtype'] == fromtype and data['totype'] == totype:
        #             data['characteristics'] = {
        #                 'delay': delay,
        #                 'drop': drop,
        #                 'corruption': corruption
        #             }

        # # Parse links characteristics
        # characteristics_by_links = config_data.get("links_characteristics", [])
        # for characteristic in characteristics_by_links:
        #     u = characteristic['from']
        #     v = characteristic['to']
        #     delay = characteristic.get('delay', {})
        #     drop = characteristic.get('drop', {})
        #     corruption = characteristic.get('corruption', {})
        #     if graph.has_edge(u, v):
        #         graph[u][v]['characteristics'] = {
        #             'delay': delay,
        #             'drop': drop,
        #             'corruption': corruption
        #         }

        return graph
