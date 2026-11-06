/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.ifl;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.Set;
import java.util.stream.Collectors;

import org.TwinCR.argus_backends.common.core.config.ConfigCommon;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import io.nats.client.Connection;
import io.nats.client.Message;

public class InformationFlowModelLayout {
    private static final int WIDTH   = 1200;
    private static final int HEIGHT  = 800;
    private static final int PADDING = 50;

    // Spring layout parameters
    private static final int    ITERATIONS       = 300;
    private static final double SPRING_LENGTH    = 30.0;
    private static final double COLISION_RADIUS  = 5.0;
    private static final double SPRING_STRENGTH  = 0.05;
    private static final double CENTER_STRENGTH  = 0.001;
    private static final double REPULSION        = 500.0;
    private static final double DAMPING          = 0.85;

    private static Connection nats = null;
    private static String requestTopic = null;
    private static Set<Link> links = null;
    private static Set<String> nodeIds = null;
    private static List<GeoFeature> geo = null;
    private static List<String> cycosimNodes = null;

    public static void load(Connection nats, String requestTopic, ConfigCommon config) {
        InformationFlowModelLayout.nats = nats;
        InformationFlowModelLayout.requestTopic = requestTopic;

        // Load links
        try {
            String cyberJson = Files.readString(config.IflConfigPath());
            JsonNode root = new ObjectMapper().readTree(cyberJson);
            links = new HashSet<>();
            nodeIds = new HashSet<>();
            for (JsonNode node : root.get("links")) {
                String from = node.get("from").asText();
                String to   = node.get("to").asText();
                links.add(new Link(from, to));
                nodeIds.add(from);
                nodeIds.add(to);
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to load cyber config: " + config.IflConfigPath(), e);
        }

        // Load geo data
        geo = new ArrayList<>();
        config.geoDataPath().ifPresent(path -> {
            try {
                String geoJson = Files.readString(path);
                JsonNode root = new ObjectMapper().readTree(geoJson);
                geo = new ArrayList<>();
                for (JsonNode feature : root.get("features")) {
                    JsonNode props = feature.get("properties");
                    String code = props.get("code_poste").asText();
                    JsonNode point = props.get("geo_point_poste");
                    double latitude  = point.get(0).asDouble();  // [lat, lon]
                    double longitude = point.get(1).asDouble();
                    geo.add(new GeoFeature(code, longitude, latitude));
                }
            } catch (IOException e) {
                throw new RuntimeException("Failed to load geo data: " + path, e);
            }
        });

        // Load cycosim nodes
        cycosimNodes = new ArrayList<>();
        config.cycosimConfigPath().ifPresent(path -> {
            try {
                String cycosimJson = Files.readString(path);
                JsonNode root = new ObjectMapper().readTree(cycosimJson);
                cycosimNodes = new ArrayList<>();
                for (JsonNode node : root.get("cycosim_nodes"))
                    cycosimNodes.add(node.asText());
            } catch (IOException e) {
                throw new RuntimeException("Failed to load cycosim config: " + path, e);
            }
        });
    }

    public record LayoutResult(Map<String, Node> nodes, Set<Link> links) {}

    // Get the path from source to destination by asking the Orchestrator
    private static List<String> findPath(String source, String destination) {
        if (nats == null)
            throw new IllegalStateException("InformationFlowModelLayout: call load() before compute()");

        try {
            ObjectMapper mapper = new ObjectMapper();
            String payload = mapper.writeValueAsString(Map.of(
                "command",     "get_path_characteristics",
                "source",      source,
                "destination", destination
            ));

            Message reply = nats.request(
                requestTopic,
                payload.getBytes(StandardCharsets.UTF_8),
                Duration.ofSeconds(10)
            );

            if (reply == null)
                throw new RuntimeException("findPath NATS request failed: timeout");

            JsonNode root = mapper.readTree(reply.getData());
            JsonNode replyNode = root.get("reply");
            if (replyNode == null)
                return List.of();  // No path found, silently skip (maybe network is not fully connected)

            List<String> result = new ArrayList<>();
            for (JsonNode n : replyNode.get("node_names"))
                result.add(n.asText());
            return result;

        } catch (IOException | InterruptedException e) {
            throw new RuntimeException("findPath NATS request failed", e);
        }
    }

    public static LayoutResult compute() {
        return compute(Optional.empty(), 0);
    }

    public static LayoutResult compute(Optional<Set<String>> selectedNodeIds, int depth) {
        if (links == null)
            throw new IllegalStateException("InformationFlowModelLayout: call load() before compute()");

        // Build node map
        Map<String, Node> nodesMap = new LinkedHashMap<>();
        for (Link link : links) {
            nodesMap.computeIfAbsent(link.from(), Node::new);
            nodesMap.computeIfAbsent(link.to(),   Node::new);
            nodesMap.get(link.from()).degree++;
            nodesMap.get(link.to()).degree++;
        }

        for (String id : cycosimNodes) {
            Node node = nodesMap.get(id);
            if (node != null)
                node.cycosimNode = true;
        }

        // Filter to selected nodes + paths between selected nodes + depth (if selection provided, else show full network)
        Set<Link> visibleLinks = links;
        if (selectedNodeIds.isPresent()) {
            Set<String> selected = selectedNodeIds.get();
            for (String id : selected) {
                if (!nodesMap.containsKey(id))
                    throw new IllegalArgumentException("Selected node not found in graph: " + id);
            }

            // Expand: add all nodes on paths between each pair of selected nodes
            List<String> selectedList = new ArrayList<>(selected);
            Set<String> visibleIds = new LinkedHashSet<>(selected);
            for (int i = 0; i < selectedList.size(); i++) {
                for (int j = i + 1; j < selectedList.size(); j++) {
                    List<String> path = findPath(selectedList.get(i), selectedList.get(j));
                    visibleIds.addAll(path);  // empty path is silently skipped
                }
            }

            // Expand: BFS outward `depth` hops from selected nodes (not path nodes)
            if (depth > 0) {
                // Build adjacency from the full link list for BFS
                Map<String, Set<String>> adjacencyMap = new HashMap<>();
                for (Link link : links) {
                    adjacencyMap.computeIfAbsent(link.from(), k -> new HashSet<>()).add(link.to());
                    adjacencyMap.computeIfAbsent(link.to(),   k -> new HashSet<>()).add(link.from());
                }
                Set<String> frontier = new HashSet<>(selected);
                for (int hop = 0; hop < depth; hop++) {
                    Set<String> nextFrontier = new HashSet<>();
                    for (String id : frontier) {
                        for (String neighbor : adjacencyMap.getOrDefault(id, Set.of())) {
                            nextFrontier.add(neighbor);
                        }
                    }
                    visibleIds.addAll(nextFrontier);
                    frontier = nextFrontier;
                }
            }

            // Filter: keep only nodes and links that are fully within visibleIds
            nodesMap.keySet().retainAll(visibleIds);
            visibleLinks = links.stream()
                .filter(l -> visibleIds.contains(l.from()) && visibleIds.contains(l.to()))
                .collect(Collectors.toSet());
        }

        if (geo != null) {
            for (GeoFeature feature : geo) {
                String code = "RTU_ICCP_" + feature.codePoste();
                Node node = nodesMap.get(code);
                if (node == null) {
                    // Search node starting with code if strict match not found
                    node = nodesMap.values().stream()
                        .filter(n -> n.id.startsWith(code))
                        .findFirst()
                        .orElse(null);
                }
                if (node != null) {
                    node.x = feature.longitude();
                    node.y = -feature.latitude();
                    node.fixed = true;
                }
            }
        }

        // Set nodes with geo-position as fixed nodes
        List<Node> fixedNodes = nodesMap.values().stream().filter(n -> n.fixed).toList();
        if (!fixedNodes.isEmpty()) {
            double minX = fixedNodes.stream().mapToDouble(n -> n.x).min().getAsDouble();
            double maxX = fixedNodes.stream().mapToDouble(n -> n.x).max().getAsDouble();
            double minY = fixedNodes.stream().mapToDouble(n -> n.y).min().getAsDouble();
            double maxY = fixedNodes.stream().mapToDouble(n -> n.y).max().getAsDouble();

            for (Node node : fixedNodes) {
                node.x = linearScale(node.x, minX, maxX, PADDING, WIDTH - PADDING);
                node.y = linearScale(node.y, minY, maxY, PADDING, HEIGHT - PADDING);
            }
        }

        // Set nodes without geo-position as free nodes with random initial position
        Random rng = new Random(42);
        for (Node node : nodesMap.values()) {
            if (!node.fixed) {
                node.x = PADDING + rng.nextDouble() * (WIDTH  - 2 * PADDING);
                node.y = PADDING + rng.nextDouble() * (HEIGHT - 2 * PADDING);
            }
        }

        // Spring layout for free nodes
        List<Node> allNodes  = new ArrayList<>(nodesMap.values());
        List<Node> freeNodes = allNodes.stream().filter(n -> !n.fixed).toList();

        // Scale repulsion with node count so spread stays reasonable for large graphs
        double repulsion = REPULSION / Math.max(1, allNodes.size() / 10.0);

        double[] vx = new double[allNodes.size()];
        double[] vy = new double[allNodes.size()];
        Map<String, Integer> idx = new HashMap<>();
        for (int i = 0; i < allNodes.size(); i++) idx.put(allNodes.get(i).id, i);

        for (int iter = 0; iter < ITERATIONS; iter++) {
            double[] fx = new double[allNodes.size()];
            double[] fy = new double[allNodes.size()];

            // Repulsion between all pairs
            for (int i = 0; i < allNodes.size(); i++) {
                for (int j = i + 1; j < allNodes.size(); j++) {
                    Node a = allNodes.get(i);
                    Node b = allNodes.get(j);
                    double dx = a.x - b.x;
                    double dy = a.y - b.y;
                    double dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1.0);
                    double force = repulsion / (dist * dist);
                    double nx = dx / dist * force;
                    double ny = dy / dist * force;
                    fx[i] += nx;  fy[i] += ny;
                    fx[j] -= nx;  fy[j] -= ny;

                    // Collision force: push apart nodes that overlap
                    double minDist = COLISION_RADIUS * 2;
                    if (dist < minDist) {
                        double overlap = (minDist - dist) / dist * 0.5;
                        fx[i] += dx * overlap;
                        fy[i] += dy * overlap;
                        fx[j] -= dx * overlap;
                        fy[j] -= dy * overlap;
                    }
                }
            }

            // Spring attraction along edges
            for (Link link : visibleLinks) {
                int si = idx.get(link.from());
                int ti = idx.get(link.to());
                Node s = allNodes.get(si);
                Node t = allNodes.get(ti);
                double dx = t.x - s.x;
                double dy = t.y - s.y;
                double dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1.0);
                double force = (dist - SPRING_LENGTH) * SPRING_STRENGTH;
                double nx = dx / dist * force;
                double ny = dy / dist * force;
                fx[si] += nx;  fy[si] += ny;
                fx[ti] -= nx;  fy[ti] -= ny;
            }

            // Centering force: weak pull toward canvas center to prevent drift
            double centerX = WIDTH  / 2.0;
            double centerY = HEIGHT / 2.0;
            for (Node node : freeNodes) {
                int i = idx.get(node.id);
                fx[i] += (centerX - node.x) * CENTER_STRENGTH;
                fy[i] += (centerY - node.y) * CENTER_STRENGTH;
            }

            // Update velocities and positions
            for (Node node : freeNodes) {
                int i = idx.get(node.id);
                vx[i] = (vx[i] + fx[i]) * DAMPING;
                vy[i] = (vy[i] + fy[i]) * DAMPING;
                vx[i] = Math.min(vx[i], SPRING_LENGTH);  // Avoid degeneracy on large networks
                vy[i] = Math.min(vy[i], SPRING_LENGTH);
                node.x += vx[i];
                node.y += vy[i];
            }
        }

        // Clamp all free nodes to canvas bounds
        for (Node node : freeNodes) {
            node.x = Math.max(PADDING, Math.min(WIDTH  - PADDING / 2, node.x));
            node.y = Math.max(PADDING, Math.min(HEIGHT - PADDING / 2, node.y));
        }

        return new LayoutResult(nodesMap, visibleLinks);
    }

    public static List<String> getNodeIds() {
        if (nodeIds == null)
            throw new IllegalStateException("Graph not loaded: call load() before getNodeIds()");
        return nodeIds.stream().sorted().toList();
    }

    private static double linearScale(double value, double domainMin, double domainMax,
                                      double rangeMin, double rangeMax) {
        if (domainMax == domainMin) return (rangeMin + rangeMax) / 2.0;
        return rangeMin + (value - domainMin) / (domainMax - domainMin) * (rangeMax - rangeMin);
    }
}
