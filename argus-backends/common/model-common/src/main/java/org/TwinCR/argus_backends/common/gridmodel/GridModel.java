/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.powsybl.iidm.network.*;
import com.powsybl.iidm.network.extensions.Coordinate;
import com.powsybl.iidm.network.extensions.SubstationPosition;
import com.powsybl.iidm.network.extensions.SubstationPositionAdder;

public class GridModel {
    private static final Logger LOGGER = LoggerFactory.getLogger(GridModel.class);
    private static final double EPSILON = 1e-6;

    public static Network network = null;
    protected static Map<String, NetworkTableExtractor.NetworkTable> networkStaticParameters;
    public static ProtectionEquipmentModel protectionEquipmentModel = null;
    // Split transformer id -> the leg of the merged three windings transformer it became
    private static Map<String, Leg> splitTransformerLegs = Map.of();

    private record Leg(String transformerId, ThreeSides side, String voltageLevelId) {}

    // The leg of a merged three windings transformer that a split transformer's side became.
    public record ThreeWindingsLeg(String transformerId, String side) {}

    public static void load(Path name, Path tiMappedPath, Optional<Path> geoJsonPath) throws IOException {
        network = Network.read(name);
        splitTransformerLegs = indexSplitTransformerLegs(network);
        GroundDisconnectors.addTo(network, tiMappedPath);
        protectionEquipmentModel = new ProtectionEquipmentModel(tiMappedPath);
        geoJsonPath.ifPresent(GridModel::addSubstationPositions);
        networkStaticParameters = NetworkTableExtractor.extractAll(network);
    }

    // A case whose three windings transformers were merged names them "leg1Id-leg2Id-leg3Id"
    // Return a mapping "legId" -> the ThreeWindingsTransformer.Leg
    private static Map<String, Leg> indexSplitTransformerLegs(Network network) {
        Map<String, Leg> legs = new HashMap<>();
        for (ThreeWindingsTransformer transformer : network.getThreeWindingsTransformers()) {
            String[] splitIds = splitIdsOf(transformer).orElse(null);
            if (splitIds == null) {
                LOGGER.warn("Three windings transformer {} is not named after its legs, the split ids published for it cannot be mapped", transformer.getId());
                continue;
            }
            int index = 0;
            for (ThreeWindingsTransformer.Leg leg : transformer.getLegs()) {
                ThreeSides side = ThreeSides.values()[index];
                legs.put(splitIds[index], new Leg(transformer.getId(), side, leg.getTerminal().getVoltageLevel().getId()));
                index++;
            }
        }
        return Collections.unmodifiableMap(legs);
    }

    private static Optional<String[]> splitIdsOf(ThreeWindingsTransformer transformer) {
        String[] splitIds = transformer.getId().split("-");
        return splitIds.length == ThreeSides.values().length ? Optional.of(splitIds) : Optional.empty();
    }

    public static Optional<String> splitLegId(ThreeWindingsTransformer transformer, ThreeSides side) {
        return splitIdsOf(transformer).map(splitIds -> splitIds[side.getNum() - 1]);
    }

    public static boolean isSplitTransformer(String equipmentId) {
        return splitTransformerLegs.containsKey(equipmentId);
    }

    // Empty when that side of the split transformer faced the fake bus, which the merge removed.
    public static Optional<ThreeWindingsLeg> mergedLeg(String splitTransformerId, String voltageLevelId) {
        Leg leg = splitTransformerLegs.get(splitTransformerId);
        if (leg == null || !leg.voltageLevelId().equals(voltageLevelId)) {
            return Optional.empty();
        }
        return Optional.of(new ThreeWindingsLeg(leg.transformerId(), leg.side().name()));
    }

    public static Map<String, NetworkTableExtractor.NetworkTable> getNetworkStaticParameters() {
        return networkStaticParameters;
    }

    public static JsonNode getSubstationsWithVoltageLevels() {
        ObjectMapper mapper = new ObjectMapper();
        ArrayNode substationsArray = mapper.createArrayNode();

        for (Substation substation : network.getSubstationStream().toList()) {
            ObjectNode substationNode = mapper.createObjectNode();
            substationNode.put("substation_id", substation.getId());

            ArrayNode voltageLevelsArray = mapper.createArrayNode();

            for (VoltageLevel vl : substation.getVoltageLevelStream().toList()) {
                ObjectNode vlNode = mapper.createObjectNode();
                vlNode.put("vl_id", vl.getId());
                vlNode.put("nominalVoltage", vl.getNominalV());
                voltageLevelsArray.add(vlNode);
            }

            substationNode.set("voltageLevels", voltageLevelsArray);
            substationsArray.add(substationNode);
        }

        return substationsArray;
    }

    public static void updatePhysicalValue(String equipmentId, String side, String kind, double value) {
        if (!Set.of("P", "Q", "U", "angle", "state", "tap").contains(kind)) {
            return;
        }

        Identifiable<?> equipment = network.getIdentifiable(equipmentId);
        if (equipment == null) {
            LOGGER.warn(equipmentId + " not found in network");
            return;
        }

        switch (kind) {
            case "state":
                boolean isOpen = value == 1;  // 2 is closed
                if (equipment instanceof Switch sw) {
                    sw.setOpen(isOpen);
                } else if (equipment instanceof Connectable<?> con) {
                    // Only in bus-breaker topology: in node-breaker, the topology is given by the switch states, and
                    // connect()/disconnect() would change the switches (e.g. close the breakers of an open line)
                    boolean nodeBreaker = con.getTerminals().stream()
                        .anyMatch(t -> t.getVoltageLevel().getTopologyKind() == TopologyKind.NODE_BREAKER);
                    if (nodeBreaker) {
                        break;
                    }
                    if (isOpen) {
                        con.disconnect();
                    } else {
                        con.connect();
                    }
                }
                break;

            case "P":
            case "Q": {
                // Avoid sign flickering for HMI
                if (Math.abs(value) < EPSILON) {
                    value = 0;
                }
                Terminal terminal = resolveTerminal(equipment, side);
                if (terminal == null) {
                    return;
                }

                Double generatorConvention = 1.0;
                if (equipment instanceof Generator || equipment instanceof Battery) {
                    generatorConvention = -1.0;
                }

                if (kind.equals("P")) {
                    terminal.setP(generatorConvention * value);
                } else {
                    terminal.setQ(generatorConvention * value);
                }
                break;
            }
            case "U":
            case "angle": {
                if (equipment instanceof Bus b) {
                    if (kind.equals("U")) {
                        b.setV(value);
                    } else {
                        b.setAngle(value);
                    }
                } else {
                    Terminal terminal = resolveTerminal(equipment, side);
                    if (terminal == null) return;
                    Bus bus = terminal.getBusView().getBus();
                    if (bus == null) return;
                    if (kind.equals("U")) {
                        bus.setV(value);
                    } else {
                        bus.setAngle(value);
                    }
                }
                break;
            }
            case "tap": {
                if (!(equipment instanceof TwoWindingsTransformer transformer)) {
                    LOGGER.warn("Tap value for {}, which is not a two windings transformer", equipmentId);
                    return;
                }
                // As in Dynawo (DYNModelTwoWindingsTransformer): use the phase tap changer when there are both a phase tap and a ratio tap
                TapChanger<?, ?, ?, ?> tapChanger = transformer.getPhaseTapChanger() != null
                    ? transformer.getPhaseTapChanger()
                    : transformer.getRatioTapChanger();
                if (tapChanger == null) {
                    LOGGER.warn("Tap value for {}, which has no tap changer", equipmentId);
                    return;
                }
                int tapPosition = (int) Math.round(value);
                if (tapPosition < tapChanger.getLowTapPosition() || tapPosition > tapChanger.getHighTapPosition()) {
                    LOGGER.warn("Tap {} out of [{}, {}] for {}, skipped", tapPosition, tapChanger.getLowTapPosition(), tapChanger.getHighTapPosition(), equipmentId);
                    return;
                }
                tapChanger.setTapPosition(tapPosition);
                break;
            }
            default:
                LOGGER.error("Unreachable");
                break;
        }
    }

    static private Terminal resolveTerminal(Identifiable<?> identifiable, String side) {
        // Injection (1 terminal)
        if (identifiable instanceof Injection<?> injection) {
            return injection.getTerminal();
        }

        // Branch (2 terminals)
        if (identifiable instanceof Branch<?> branch) {
            if (side == null) return null;
            return (side.equals("ONE") || side.equals("1"))
                ? branch.getTerminal1()
                : branch.getTerminal2();
        }

        // Three-windings transformer (3 terminals)
        if (identifiable instanceof ThreeWindingsTransformer t3) {
            if (side == null) return null;
            ThreeSides threeSide = switch (side) {
                case "ONE" -> ThreeSides.ONE;
                case "1" -> ThreeSides.ONE;
                case "TWO" -> ThreeSides.TWO;
                case "2" -> ThreeSides.TWO;
                case "THREE" -> ThreeSides.THREE;
                case "3" -> ThreeSides.THREE;
                default -> null;
            };
            return threeSide != null
                ? t3.getTerminal(threeSide)
                : null;
        }

        return null;
    }

    private static void addSubstationPositions(Path geoJsonPath) {
        Map<String, double[]> positions = new HashMap<>();
        try {
            JsonNode root = new ObjectMapper().readTree(geoJsonPath.toFile());
            for (JsonNode feature : root.path("features")) {
                JsonNode props = feature.path("properties");
                JsonNode codeNode = props.path("code_poste");
                if (codeNode.isMissingNode() || codeNode.isNull()) continue;
                String code = codeNode.asText();
                JsonNode coords = props.path("geo_point_poste");
                if (code != null && coords.isArray() && coords.size() == 2) {
                    positions.put(code, new double[]{coords.get(0).asDouble(), coords.get(1).asDouble()});
                }
            }
        } catch (IOException e) {
            LOGGER.error("Failed to read geo JSON file: {}", geoJsonPath, e);
            return;
        }

        // Apply extensions
        for (Map.Entry<String, double[]> entry : positions.entrySet()) {
            Substation substation = network.getSubstation(entry.getKey());
            if (substation == null) {
                LOGGER.warn("GeoJSON entry '{}' has no matching substation in network", entry.getKey());
                continue;
            }
            double[] coords = entry.getValue();
            substation.newExtension(SubstationPositionAdder.class)
                .withCoordinate(new Coordinate(coords[0], coords[1]))
                .add();
        }

        // Warn on substations still missing a position
        network.getSubstations().forEach(s -> {
            if (s.getExtension(SubstationPosition.class) == null) {
                LOGGER.warn("Substation '{}' has no position extension after geo JSON loading", s.getId());
            }
        });
    }
}
