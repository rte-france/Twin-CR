/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#ifndef NETWORK_GRAPH_H
#define NETWORK_GRAPH_H

#include "CommunicationElements.h"
#include "CommunicationLinks.h"
#include "CommunicationNodes.h"

#include <graaflib/graph.h>
#include <graaflib/types.h>
#include <nlohmann/json.hpp>
#include <spdlog/spdlog.h>

#include <atomic>
#include <cassert>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>


struct PairHash {
    std::size_t operator()(const std::pair<std::size_t, std::size_t>& p) const noexcept {
        std::size_t h1 = std::hash<std::size_t>{}(p.first);
        std::size_t h2 = std::hash<std::size_t>{}(p.second);
        return h1 ^ (h2 << 1); // Or use any other good mixing function
    }

    template <class T1, class T2>
    std::size_t operator()(const std::pair<T1, T2>& p) const noexcept {
        auto h1 = std::hash<T1>{}(p.first);
        auto h2 = std::hash<T2>{}(p.second);
        h1 ^= h2 + 0x9e3779b9 + (h1 << 6) + (h1 >> 2);  // Hash function from boost
        return h1;
    }

    template<class Archive>
    void serialize(Archive& ar) {
        ar();
    }
};
CHECK_SERIALIZABLE(PairHash);

class NetworkGraph {
    public:
        NetworkGraph(std::filesystem::path cyber_config_path, const std::string& scada_location, std::optional<nlohmann::json> cycosim_config);

        NetworkGraph() = default;  // Default constructor needed for deserialization

        CommunicationNode& getNode(graaf::vertex_id_t id) const { return *graph_fast_node_accesser_[id]; }
        std::shared_ptr<CommunicationNode> getNodePtr(graaf::vertex_id_t id) { return graph_fast_node_accesser_[id]; }

        CommunicationLink& getLink(graaf::vertex_id_t source, graaf::vertex_id_t destination) const {
            auto it = graph_fast_link_accesser_.find({source, destination});
            assert(it != graph_fast_link_accesser_.end());  // Only checks in debug mode
            return *it->second;
        }
        std::shared_ptr<CommunicationLink> getLinkPtr(graaf::vertex_id_t source, graaf::vertex_id_t destination) {
            auto it = graph_fast_link_accesser_.find({source, destination});
            assert(it != graph_fast_link_accesser_.end());  // Only checks in debug mode
            return it->second;
        }

        void addMonitoredPaths(const std::string& scada_location);

        /**
         * New unique identifier for a control (ControlSent::control_uid). Thread-safe.
         */
        int64_t nextControlUid() { return next_control_uid_.fetch_add(1); }

        /**
         * Get the list of vertices (by vertex_id) from the CommunicationNode with name 'source' to the one with name 'destination'
         */
        std::vector<graaf::vertex_id_t> getPath(std::string source, std::string destination);

        /**
         * Set the characteristics of the node with name "node_name". The characteristics are read from the "characteristics" json.
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void addCharacteristicsToNode(std::string node_name, const nlohmann::json::basic_json::value_type& characteristics, Mode mode=Mode::Execute);

        /**
         * Set the characteristics of the link from "source" to "destination". The characteristics are read from the "characteristics" json.
         * If mode is set to Validate, the function_config is parsed (checking for errors), but not actually implemented
         * If mode is set to Execute, it is parsed and actually implemented
         */
        void addCharacteristicsToLink(std::string source, std::string destination, const nlohmann::json::basic_json::value_type& characteristics, Mode mode=Mode::Execute);

        CommunicationLink& getLinkOrThrow(std::string source, std::string destination) const {
            if (!node_name_to_id_.contains(source))
                throw std::invalid_argument(source + " does not exist");
            if (!node_name_to_id_.contains(destination))
                throw std::invalid_argument(destination + " does not exist");

            auto source_id = node_name_to_id_.at(source);
            auto destination_id = node_name_to_id_.at(destination);
            auto it = graph_fast_link_accesser_.find({source_id, destination_id});
            if (it == graph_fast_link_accesser_.end())
                throw std::invalid_argument("No link from " + source + " to " + destination + " exists");
            return *it->second;
        }

        nlohmann::json getLinkConfig(const std::string& source, const std::string& destination) {
            return getLinkOrThrow(source, destination).getElementConfig();
        }

        /**
         * Return all nodes in alphabetical order
         */
        std::vector<std::string> listNodes() const {
            std::vector<std::string> names;
            names.reserve(node_name_to_id_.size());
            for (auto& [name, id] : node_name_to_id_) names.push_back(name);
            std::sort(names.begin(), names.end());
            return names;
        }

        /**
         * Return all nodes that can be reached in one hop from 'source'
         */
        std::vector<std::string> listDestinations(const std::string& source) const {
            if (!node_name_to_id_.contains(source)) return {};
            std::vector<std::string> names;
            for (auto neighbour : graph_.get_neighbors(node_name_to_id_.at(source))) {
                names.push_back(getNode(neighbour).getName());
            }
            std::sort(names.begin(), names.end());
            return names;
        }

        nlohmann::json getNodeConfig(const std::string& node_name) {
            if (!node_name_to_id_.contains(node_name))
                throw std::invalid_argument(node_name + " does not exist");
            return getNode(node_name_to_id_[node_name]).getElementConfig();
        }

        nlohmann::json getPathConfig(const std::string& source, const std::string& destination);

        // Serialization
        template<class Archive>
        void save(Archive& ar) const {
            int64_t next_control_uid = next_control_uid_.load();
            ar(graph_.get_vertices(), graph_.get_edges(), graph_fast_node_accesser_, graph_fast_link_accesser_, node_name_to_id_, link_names_, monitored_paths_, computed_routes_, next_control_uid);
        }

        template <class Archive>
        void load(Archive& ar) {
            std::unordered_map<graaf::vertex_id_t, std::shared_ptr<CommunicationNode>> vertices;
            std::unordered_map<graaf::edge_id_t, std::shared_ptr<CommunicationLink>, graaf::edge_id_hash> edges;
            int64_t next_control_uid;
            ar(vertices, edges, graph_fast_node_accesser_, graph_fast_link_accesser_, node_name_to_id_, link_names_, monitored_paths_, computed_routes_, next_control_uid);
            next_control_uid_.store(next_control_uid);
            // The back-pointer of the monitored paths is not serialized
            for (auto& monitored_path : monitored_paths_) {
                monitored_path->setNetworkGraph(*this);
            }

            // Rebuild graph manually as it cannot be automatically serialized
            for (graaf::vertex_id_t i = 0; i < graph_fast_node_accesser_.size(); i++) {
                graaf::vertex_id_t node_id = graph_.add_vertex(graph_fast_node_accesser_[i]);
                if (node_id != i) {
                    spdlog::critical("{} != {}", node_id, i);
                    throw std::runtime_error("Expected graaf node_id to be incremented one by one for each element");
                }
            }
            for (auto& [key, edge] : edges) {
                graph_.add_edge(key.first, key.second, edge);
            }
        }

    private:
        void addCommunicationNodeToGraph(std::string name, std::string type);
        void addCommunicationLinkToGraph(std::string source, std::string destination, std::string channel_type);
        std::optional<std::vector<graaf::vertex_id_t>> breadthFirstSearchWithCache(graaf::vertex_id_t source, graaf::vertex_id_t destination);

        /**
         * Given a path A->B->C->D, cache the subpaths with keys (source, destination) = (A,D), (B,D), (C,D)
         */
        void cacheSubpathsToDestination(const std::vector<graaf::vertex_id_t>& path);

        template <typename V, typename E>
        static void checkRouteUniqueness(const graaf::undirected_graph<V, E>& graph, graaf::vertex_id_t root, const graaf::vertex_id_t* root_root, std::unordered_set<graaf::vertex_id_t>& seen_vertices, std::unordered_set<graaf::vertex_id_t>& duplicate_vertices);

        graaf::directed_graph<std::shared_ptr<CommunicationNode>, std::shared_ptr<CommunicationLink>> graph_;
        std::vector<std::shared_ptr<CommunicationNode>> graph_fast_node_accesser_;
        std::unordered_map<std::pair<graaf::vertex_id_t, graaf::vertex_id_t>, std::shared_ptr<CommunicationLink>, PairHash> graph_fast_link_accesser_;
        std::unordered_map<std::string, graaf::vertex_id_t> node_name_to_id_;
        std::unordered_set<std::string> link_names_;
        std::vector<std::shared_ptr<MonitoredPath>> monitored_paths_;
        std::unordered_map<std::pair<graaf::vertex_id_t, graaf::vertex_id_t>, std::vector<graaf::vertex_id_t>, PairHash> computed_routes_;
        std::unordered_set<std::string> cycosim_nodes_;
        std::atomic<int64_t> next_control_uid_ = 1;
};

#endif // NETWORK_GRAPH_H
