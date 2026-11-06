/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#include "NetworkGraph.h"
#include "CommunicationNodes.h"
#include "CycosimNode.h"
#include "Orchestrator.h"
#include "RTU.h"

#include <graaflib/algorithm/shortest_path/bfs_shortest_path.h>
#include "graaflib/types.h"
#include <mimalloc.h>
#include <optional>
#include <regex>
#include <spdlog/spdlog.h>

#include <cassert>
#include <memory>
#include <stdexcept>
#include <unordered_set>
#include <fstream>
#include <vector>


NetworkGraph::NetworkGraph(std::filesystem::path cyber_config_path, const std::string& scada_location, std::optional<nlohmann::json> cycosim_config) {
    auto config = nlohmann::json::parse(std::ifstream(cyber_config_path));

    if (!config.contains("links"))
        throw std::runtime_error("Cyber configs does not contains 'links'");

    auto links = config["links"];

    graaf::undirected_graph<std::string, std::string> undirected_graph;  // Temporary graph used to identify non-unique routes
    std::unordered_map<std::string, graaf::vertex_id_t> undirected_graph_node_name_to_id;

    if (cycosim_config.has_value()) {
        cycosim_nodes_ = cycosim_config.value()["cycosim_nodes"];
    }

    // Parse elements from links (including nodes)
    for (auto link: links) {
        try {
            std::string source = link["from"];
            std::string source_type = link["fromtype"];
            std::string destination = link["to"];
            std::string destination_type = link["totype"];

            addCommunicationNodeToGraph(source, source_type);
            addCommunicationNodeToGraph(destination, destination_type);

            std::string channel_type = source_type + "2" + destination_type;
            addCommunicationLinkToGraph(source, destination, channel_type);
            // Assume bidirectionnal links
            channel_type = destination_type + "2" + source_type;
            addCommunicationLinkToGraph(destination, source, channel_type);

            // Also construct undirected graph
            if (!undirected_graph_node_name_to_id.contains(source)) {
                const auto node_graph_id = undirected_graph.add_vertex(source);
                undirected_graph_node_name_to_id[source] = node_graph_id;
            }
            if (!undirected_graph_node_name_to_id.contains(destination)) {
                const auto node_graph_id = undirected_graph.add_vertex(destination);
                undirected_graph_node_name_to_id[destination] = node_graph_id;
            }
            undirected_graph.add_edge(undirected_graph_node_name_to_id[destination], undirected_graph_node_name_to_id[source], source + "2" + destination);

        } catch (const nlohmann::detail::type_error& e) {
            throw std::invalid_argument("Invalid link: " + std::string(e.what()) + " in:\n" + link.dump());
        }
    }

    // Check for uniqueness of routes to and from all nodes by traversing the graph
    std::unordered_set<graaf::vertex_id_t> seen_vertices = {};
    std::unordered_set<graaf::vertex_id_t> duplicate_vertices = {};
    bool err = false;
    auto start_node = undirected_graph.get_vertices().begin();
    if (start_node == undirected_graph.get_vertices().end())
        throw std::invalid_argument("Graph is empty");
    checkRouteUniqueness(undirected_graph, start_node->first, nullptr, seen_vertices, duplicate_vertices);
    for (auto vertex : duplicate_vertices) {
        spdlog::critical("Multiple paths from {} to {}", undirected_graph.get_vertex(vertex), start_node->second);
        err = true;
    }
    if (err)
        throw std::runtime_error("Invalid graph");

    // Parse nodes individual characteristics
    std::unordered_set<std::string> nodes_with_specific_characteristics;
    if (config.contains("nodes_characteristics")) {
        for (auto node_charactistics : config["nodes_characteristics"]) {
            std::string node_name = node_charactistics["node"];
            if (!node_name_to_id_.contains(node_name)) {
                spdlog::warn("Setting characteristics for node {} that does not exist", node_name);
                continue;
            }
            nodes_with_specific_characteristics.insert(node_name);
            addCharacteristicsToNode(node_name, node_charactistics);
        }
    }

    // Parse nodes generic characteristics (for nodes without individual specifications)
    if (config.contains("nodes_characteristics_by_node_type")) {
        for (auto node_characteristics : config["nodes_characteristics_by_node_type"]) {
            std::string node_type = node_characteristics["type"];
            for (const auto& [key, node] : graph_.get_vertices()) {
                if (node->getType() == node_type && !nodes_with_specific_characteristics.contains(node->getName())) {
                    addCharacteristicsToNode(node->getName(), node_characteristics);
                }
            }
        }
    }

    // Parse links individual characteristics
    std::unordered_set<std::string> links_with_specific_characteristics;
    if (config.contains("links_characteristics")) {
        for (auto link_charactistics : config["links_characteristics"]) {
            std::string source = link_charactistics["from"];
            std::string destination = link_charactistics["to"];
            if (!link_names_.contains(source + "2" + destination)) {
                spdlog::warn("Setting characteristics for link from {} to {} that does not exist", source, destination);
                continue;
            }
            links_with_specific_characteristics.insert(source + "2" + destination);
            addCharacteristicsToLink(source, destination, link_charactistics);
        }
    }

    // Parse links generic characteristics (for links without individual specifications)
    if (config.contains("links_characteristics_by_link_type")) {
        for (auto link_characteristics : config["links_characteristics_by_link_type"]) {
            std::string channel_type;
            try {
                std::string source_type = link_characteristics["fromtype"];
                std::string destination_type = link_characteristics["totype"];
                channel_type = source_type + "2" + destination_type;
            } catch (const nlohmann::detail::type_error& e) {
                throw std::invalid_argument("Invalid link characteristics: " + std::string(e.what()) + " in:\n" + link_characteristics.dump());
            }

            for (const auto& [key, link] : graph_.get_edges()) {
                if (link->getChannelType() == channel_type && !links_with_specific_characteristics.contains(link->getSource() + "2" + link->getDestination())) {
                    addCharacteristicsToLink(link->getSource(), link->getDestination(), link_characteristics);
                }
            }
        }
    }

    // Check which IFL node should publish intermediary values
    const auto& configToml = Orchestrator::get().getConfig();
    const auto& publishing_nodes_node = configToml["master"]["publishing_ifl_nodes"];
    if (publishing_nodes_node) {
        const auto* publishing_nodes = publishing_nodes_node.as_array();
        if (!publishing_nodes) {
            throw std::invalid_argument("publishing_ifl_nodes must be an array of strings (handles regexes)");
        }

        for (const auto& node : *publishing_nodes) {
            const auto* pattern = node.as_string();
            if (!pattern) {
                throw std::invalid_argument("publishing_ifl_nodes must be an array of strings (handles regexes)");
            }
            std::regex reg;
            try {
                reg = std::regex(pattern->get());
            } catch (const std::regex_error& e) {
                throw std::invalid_argument(fmt::format("Invalid regex pattern in publishing_ifl_nodes: '{}', {}", pattern->get(), e.what()));
            }

            bool match = false;
            for (const auto& [_, node] : graph_.get_vertices()) {
                const std::string& node_name = node->getName();
                spdlog::trace("Tried to match {} to pattern {}: {}", node_name, pattern->get(), std::regex_match(node_name, reg));
                if (std::regex_match(node_name, reg)) {
                    spdlog::debug("IFL node {} matched to publishing_ifl_nodes pattern {}", node_name, pattern->get());
                    node->setPublishIntermediaryInfo(true);
                    match = true;
                }
            }
            if (!match) {
                spdlog::warn("No match found for regex pattern {} in publishing_ifl_nodes", pattern->get());
            }
        }
    }

    // Workaround json not releasing memory (https://github.com/nlohmann/json/issues/1924)
    config.clear();
    mi_collect(true);

    addMonitoredPaths(scada_location);
}

namespace graaf::algorithm {

template <typename E, graph_type T, typename WEIGHT_T>
std::optional<graph_path<WEIGHT_T>> bfs_shortest_path_to_type(
    const graph<std::shared_ptr<CommunicationNode>, E, T>& graph, vertex_id_t start_vertex,
    const std::vector<std::string>& target_types) {
  std::unordered_map<vertex_id_t, detail::path_vertex<WEIGHT_T>> vertex_info{
      {start_vertex, {start_vertex, 0, start_vertex}}};

  const auto callback{[&vertex_info](const edge_id_t& edge) {
    const auto [source, target]{edge};

    if (!vertex_info.contains(target)) {
      vertex_info[target] = {target, vertex_info[source].dist_from_start + 1,
                             source};
    }
  }};

  std::optional<vertex_id_t> end_vertex;
  // We keep searching until we have reached a vertex whose type is in target_types
  const auto search_termination_strategy{
      [&end_vertex, &target_types, &graph](const vertex_id_t vertex_id) {
        if (std::find(target_types.begin(), target_types.end(), graph.get_vertex(vertex_id)->getType()) != target_types.end()) {
            end_vertex = vertex_id;
            return true;
        }
        return false;
      }};

  breadth_first_traverse(graph, start_vertex, callback,
                         search_termination_strategy);

  if (!end_vertex.has_value()) {
    return std::nullopt;
  }

  return reconstruct_path(start_vertex, *end_vertex, vertex_info);
}

}  // namespace graaf::algorithm

void NetworkGraph::addMonitoredPaths(const std::string& scada_location) {
    for (auto& [node_id, node] : graph_.get_vertices()) {
        if (node->getType() == "RTU") {
            // Link to RTU is being monitored by the closest ARP (or SCADA if no ARP between the RTU and SCADA)
            auto route = graaf::algorithm::bfs_shortest_path_to_type<std::shared_ptr<CommunicationLink>, graaf::graph_type::DIRECTED, int>(graph_, node_id, {"ARP", "SCADA"});
            if (route.has_value()) {
                auto arp_id = (*route).vertices.back();
                monitored_paths_.emplace_back(MonitoredPath::create(
                    graph_.get_vertex(arp_id)->getName(),  // Closest ARP or SCADA
                    node->getName(),  // RTU
                    *this));
            } else {
                spdlog::warn("RTU {} is not connected to an ARP nor to a SCADA", node->getName());
            }

        } else if (node->getType() == "ARP") {
            // SCADA monitors its connections with all ARPs
            monitored_paths_.emplace_back(MonitoredPath::create(scada_location, node->getName(), *this));
        }
    }
}

std::optional<std::vector<graaf::vertex_id_t>> NetworkGraph::breadthFirstSearchWithCache(graaf::vertex_id_t source, graaf::vertex_id_t destination) {
    if (computed_routes_.contains({source, destination})) {
        return computed_routes_.at({source, destination});
    }

    std::unordered_map<graaf::vertex_id_t, graaf::algorithm::detail::path_vertex<int>> vertex_info{
        {source, {source, 0, source}}};

    const auto callback{[&vertex_info](const graaf::edge_id_t& edge) {
        const auto [src, target]{edge};
        if (!vertex_info.contains(target)) {
            vertex_info[target] = {target, vertex_info[src].dist_from_start + 1, src};
        }
    }};

    // Search until we reach destination or a node for which we already have a cached path to destination (using path uniqueness)
    graaf::vertex_id_t arrival_node = destination;
    const auto search_termination_strategy{
        [&](const graaf::vertex_id_t vertex_id) {
            if (vertex_id == destination) { arrival_node = destination; return true; }
            if (vertex_id != source && computed_routes_.contains({vertex_id, destination})) {
                arrival_node = vertex_id;
                return true;
            }
            return false;
        }};

    graaf::algorithm::breadth_first_traverse(graph_, source, callback, search_termination_strategy);

    // Path from source to arrival_node
    auto prefix_path = graaf::algorithm::detail::reconstruct_path(source, arrival_node, vertex_info);
    if (!prefix_path.has_value()) {
        return std::nullopt;
    }

    // Final path is prefix_path (source to arrival) + cached path from arrival to destination
    std::vector<graaf::vertex_id_t> path(prefix_path.value().vertices.begin(), prefix_path.value().vertices.end());
    if (arrival_node != destination) {
        const auto& suffix = computed_routes_.at({arrival_node, destination});
        path.insert(path.end(), suffix.begin() + 1, suffix.end());  // + 1 to avoid including twice arrival_node
    }

    cacheSubpathsToDestination(path);
    return path;
}

void NetworkGraph::cacheSubpathsToDestination(const std::vector<graaf::vertex_id_t>& path) {
    const size_t n = path.size();
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = i + 1; j < n; ++j) {
            auto subpath = std::make_pair(path[i], path[j]);
            if (!computed_routes_.contains(subpath)) {
                computed_routes_.emplace(subpath, std::vector<graaf::vertex_id_t>(path.begin() + i, path.begin() + j + 1));
            }
        }
    }
}

std::vector<graaf::vertex_id_t> NetworkGraph::getPath(std::string source, std::string destination) {
    graaf::vertex_id_t source_id;
    graaf::vertex_id_t destination_id;
    if (!node_name_to_id_.contains(source))
        throw std::invalid_argument(source + " not in network graph");
    source_id = node_name_to_id_.at(source);

    if (!node_name_to_id_.contains(destination))
        throw std::invalid_argument(destination + " not in network graph");
    destination_id = node_name_to_id_.at(destination);

    auto route = breadthFirstSearchWithCache(source_id, destination_id);
    if (route.has_value()) {
        return route.value();
    } else {
        throw std::invalid_argument("No route found between " + source + " and " + destination);
    }
}

void NetworkGraph::addCommunicationNodeToGraph(std::string node_name, std::string node_type) {
    // Node names end up in fixed-size char[128] fields of the Broker's ring buffer (RingBuffer.h, as 'destination'/'location').
    // Reject them here, at config load, instead of during the simulation
    constexpr size_t MAX_RING_BUFFER_FIELD_LENGTH = 128;
    if (node_name.size() >= MAX_RING_BUFFER_FIELD_LENGTH) {
        throw std::invalid_argument(
            "IFL node name '" + node_name + "' is " + std::to_string(node_name.size()) +
            " characters long, exceeding the " + std::to_string(MAX_RING_BUFFER_FIELD_LENGTH - 1) + "-character limit"
        );
    }

    if (node_name_to_id_.contains(node_name)) {
        // Node already parsed, only do sanity check
        if (node_type != graph_.get_vertex(node_name_to_id_.at(node_name))->getType()) {
            throw std::runtime_error("Node " + node_name + " already exists with a different type");
        }
        return;
    }

    // Node not already parsed, add it to graph
    auto node = std::make_shared<CommunicationNode>(node_name, node_type);
    const auto node_graph_id = graph_.add_vertex(node);

    if (cycosim_nodes_.contains(node_name)) {
        node = std::make_shared<CycosimNode>(node_name, node_type);
        graph_.get_vertex(node_graph_id) = node;
    } else if (node_type == "RTU" || node_type == "ARP") {
        node = std::make_shared<RTU>(node_name, node_type, node_graph_id);
        graph_.get_vertex(node_graph_id) = node;
    }

    if (graph_fast_node_accesser_.size() != node_graph_id) {
        throw std::runtime_error("Expected graaf node_id to be incremented one by one for each element");
    }
    graph_fast_node_accesser_.push_back(node);
    node_name_to_id_[node_name] = node_graph_id;
}

void NetworkGraph::addCommunicationLinkToGraph(std::string source, std::string destination, std::string channel_type) {
    std::string link_name = source + "2" + destination;

    if (link_names_.contains(link_name))
        throw std::runtime_error("Link " + source + "-" + destination + " already exists");
    link_names_.insert(link_name);

    auto link = std::make_shared<CommunicationLink>(source, destination, channel_type);
    graph_.add_edge(node_name_to_id_[source], node_name_to_id_[destination], link);
    graph_fast_link_accesser_.insert({{node_name_to_id_[source], node_name_to_id_[destination]}, link});
}

void NetworkGraph::addCharacteristicsToNode(std::string node_name, const nlohmann::json::basic_json::value_type &characteristics, Mode mode) {
    if (!node_name_to_id_.contains(node_name))
        throw std::invalid_argument(node_name + " does not exist");
    try {
        auto& node = getNode(node_name_to_id_[node_name]);

        if (characteristics.contains("delay_function")) {
            node.setDelayFunction(characteristics["delay_function"], mode);
        }
        if (characteristics.contains("drop_function")) {
            node.setDropFunction(characteristics["drop_function"], mode);
        }
        if (characteristics.contains("corruption_functions")) {
            node.clearCorruptionFunctions(mode);
            for (const auto& corruption : characteristics["corruption_functions"]) {
                node.addCorruptionFunction(corruption, mode);
            }
        }
    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid node characteristics: " + std::string(e.what()) + " in:\n" + characteristics.dump());
    }
}

void NetworkGraph::addCharacteristicsToLink(std::string source, std::string destination, const nlohmann::json::basic_json::value_type &characteristics, Mode mode) {
    try {
        auto& link = getLinkOrThrow(source, destination);

        if (characteristics.contains("delay_function")) {
            link.setDelayFunction(characteristics["delay_function"], mode);
        }
        if (characteristics.contains("drop_function")) {
            link.setDropFunction(characteristics["drop_function"], mode);
        }
        if (characteristics.contains("corruption_functions")) {
            link.clearCorruptionFunctions(mode);
            for (const auto& corruption : characteristics["corruption_functions"]) {
                link.addCorruptionFunction(corruption, mode);
            }
        }
    } catch (const nlohmann::detail::type_error& e) {
        throw std::invalid_argument("Invalid link characteristics: " + std::string(e.what()) + " in:\n" + characteristics.dump());
    }
}

template <typename V, typename E>
void NetworkGraph::checkRouteUniqueness(const graaf::undirected_graph<V, E>& graph, graaf::vertex_id_t root, const graaf::vertex_id_t* root_root,
    std::unordered_set<graaf::vertex_id_t>& seen_vertices,
    std::unordered_set<graaf::vertex_id_t>& duplicate_vertices) {

    for (const auto& neighbor_vertex : graph.get_neighbors(root)) {
        if (root_root != nullptr && neighbor_vertex == *root_root) {
            // Avoid coming back to previous node
        } else if (seen_vertices.contains(neighbor_vertex)) {
            duplicate_vertices.insert(neighbor_vertex);
        } else {
            seen_vertices.insert(neighbor_vertex);
            checkRouteUniqueness(graph, neighbor_vertex, &root, seen_vertices, duplicate_vertices);
        }
    }
}

nlohmann::json NetworkGraph::getPathConfig(const std::string& source, const std::string& destination) {
    if (source == destination)
        throw std::invalid_argument("Path destination must be different from source");

    auto path = getPath(source, destination);
    nlohmann::json path_config;

    size_t i = 0;
    for (; i < path.size(); i++) {
        path_config["node_names"].push_back(getNode(path[i]).getName());
        path_config["node_configs"].push_back(getNode(path[i]).getElementConfig());
        if (i < path.size() - 1)
            path_config["link_configs"].push_back(getLink(path[i], path[i+1]).getElementConfig());
    }
    return path_config;
}
