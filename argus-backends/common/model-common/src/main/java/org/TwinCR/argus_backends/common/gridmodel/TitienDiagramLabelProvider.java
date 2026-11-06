/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Queue;
import java.util.Set;
import java.util.stream.Stream;

import org.TwinCR.argus_backends.common.gridmodel.ProtectionEquipmentModel.ProtectionEquipmentValue;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.powsybl.iidm.network.Branch;
import com.powsybl.iidm.network.Bus;
import com.powsybl.iidm.network.BusbarSection;
import com.powsybl.iidm.network.Injection;
import com.powsybl.iidm.network.Network;
import com.powsybl.iidm.network.Switch;
import com.powsybl.iidm.network.SwitchKind;
import com.powsybl.iidm.network.Terminal;
import com.powsybl.iidm.network.TopologyKind;
import com.powsybl.iidm.network.ThreeSides;
import com.powsybl.iidm.network.ThreeWindingsTransformer;
import com.powsybl.iidm.network.TwoSides;
import com.powsybl.iidm.network.VoltageLevel;
import com.powsybl.sld.layout.LayoutParameters;
import com.powsybl.sld.library.SldComponentLibrary;
import com.powsybl.sld.model.coordinate.Direction;
import com.powsybl.sld.model.nodes.BusNode;
import com.powsybl.sld.model.nodes.EquipmentNode;
import com.powsybl.sld.model.nodes.FeederNode;
import com.powsybl.sld.model.nodes.Node;
import com.powsybl.sld.model.nodes.NodeSide;
import com.powsybl.sld.model.nodes.feeders.FeederTwLeg;
import com.powsybl.sld.model.nodes.feeders.FeederWithSides;
import com.powsybl.sld.svg.AbstractLabelProvider;
import com.powsybl.sld.svg.DefaultLabelProvider;
import com.powsybl.sld.svg.FeederInfo;
import com.powsybl.sld.svg.LabelPosition;
import com.powsybl.sld.svg.SvgParameters;

public class TitienDiagramLabelProvider extends AbstractLabelProvider {
    Network network;
    private final boolean withMeasurementLabelProvider;

    private final ObjectMapper MAPPER = new ObjectMapper();

    private static final double PE_ROW_H = 9.0;
    private static final double PE_COL_W = 24.0;
    private static final int PE_COL_MAX = 6;

    public TitienDiagramLabelProvider(SldComponentLibrary componentLibrary, LayoutParameters layoutParameters, SvgParameters svgParameters, Network network, boolean withMeasurementLabelProvider) {
        super(componentLibrary, layoutParameters, svgParameters);
        this.network = network;
        this.withMeasurementLabelProvider = withMeasurementLabelProvider;
    }

    @Override
    public List<FeederInfo> getFeederInfos(FeederNode feederNode) {
        if (withMeasurementLabelProvider) {
            MeasurementLabelProvider labelProvider = new MeasurementLabelProvider(network, componentLibrary, layoutParameters, svgParameters);
            return labelProvider.getFeederInfos(feederNode);
        } else {
            DefaultLabelProvider labelProvider = new DefaultLabelProvider(network, componentLibrary, layoutParameters, svgParameters);
            return labelProvider.getFeederInfos(feederNode);
        }
    }

    @Override
    public List<NodeLabel> getNodeLabels(Node node, Direction direction) {
        Objects.requireNonNull(node);

        List<NodeLabel> nodeLabels = new ArrayList<>();
        if (node instanceof FeederNode feederNode) {
            // Feeder label
            getFeederLabel(feederNode).ifPresent(label -> nodeLabels.add(new NodeLabel(label, getFeederLabelPosition(node, direction), null)));
            /* if ((feederNode).getFeeder() instanceof FeederWithSides feeder) {
                // Label is set as name of the voltage level on the other side
                String labelName = feeder.getOtherSideVoltageLevelInfos().getName();
            } */

            // Protection equipments associated with the feeder
            Terminal terminal = getFeederTerminal(feederNode);
            if (terminal != null) {
                // Protections are mapped from the iidm id of the feeder (with side) or from the iidm id of the associated breaker
                String breakerId = getBreakerIdForFeeder(terminal);

                NodeSide side = getFeederSide(feederNode, terminal);

                List<ProtectionEquipmentValue> protectionEquipmentValues = Stream.concat(
                    GridModel.protectionEquipmentModel.getByEquipmentId(feederNode.getEquipmentId(), side).stream(),
                    breakerId != null ? GridModel.protectionEquipmentModel.getByEquipmentId(breakerId, null).stream() : Stream.empty()
                ).toList();

                addProtectionEquipmentLabels(nodeLabels, feederNode, protectionEquipmentValues, direction, -20,
                    63 + (withMeasurementLabelProvider ? 35 : 0),
                    -102 - (withMeasurementLabelProvider ? 40 : 0));
            }
        } else if (node instanceof BusNode) {
            BusbarSection bbs = network.getBusbarSection(node.getId());
            if (bbs != null) {
                Bus bus = bbs.getTerminal().getBusView().getBus();  // null if isolated
                if (bus != null) {
                    double voltage = bus.getV();

                    // Bus label
                    getNameOrLabelOrId(node).ifPresent(label -> nodeLabels.add(new NodeLabel(
                        label,
                        new LabelPosition("NW_LABEL", -10, -2, false, 0),
                        null
                    )));
                    // Bus voltage
                    nodeLabels.add(new NodeLabel(
                        valueFormatter.formatVoltage(voltage, "kV"),
                        new LabelPosition("VOLTAGE_LABEL", -40, 9, false, 0),
                        null
                    ));
                }
            }
        }

        return nodeLabels;
    }

    @Override
    public List<NodeDecorator> getNodeDecorators(Node node, Direction direction) {
        DefaultLabelProvider defaultLabelProvider = new DefaultLabelProvider(this.network, this.componentLibrary, this.layoutParameters, this.svgParameters);
        return defaultLabelProvider.getNodeDecorators(node, direction);
    }

    // Label that is displayed above the feeder
    private Optional<String> getFeederLabel(FeederNode feederNode) {
        ThreeWindingsTransformer transformer = network.getThreeWindingsTransformer(feederNode.getEquipmentId());
        if (transformer != null && feederNode.getFeeder() instanceof FeederWithSides feeder) {
            Optional<String> legId = GridModel.splitLegId(transformer, ThreeSides.valueOf(feeder.getSide().getIntValue()));
            if (legId.isPresent()) {
                // For three windings transformers, use the (short) leg name instead of the full transformer name
                return legId;
            }
        }
        return getNameOrLabelOrId(feederNode);
    }

    private Optional<String> getNameOrLabelOrId(Node node) {
        if (node instanceof EquipmentNode eqNode) {
            return Optional.ofNullable(node.getLabel().orElse(svgParameters.isUseName() ? eqNode.getName() : eqNode.getEquipmentId()));
        } else {
            return node.getLabel();
        }
    }

    private void addProtectionEquipmentLabels(List<NodeLabel> nodeLabels,
                                    FeederNode feederNode,
                                    List<ProtectionEquipmentValue> protectionEquipmentValues,
                                    Direction direction,
                                    int x, int yUp, int yDown) {
        if (protectionEquipmentValues.isEmpty()) return;
        int y = direction == Direction.BOTTOM ? yDown : yUp;

        for (int i = 0; i < protectionEquipmentValues.size(); i++) {
            ProtectionEquipmentValue pe = protectionEquipmentValues.get(i);
            boolean active = pe.value().toDouble() != 0.0;

            double dx = x + (i / PE_COL_MAX) * PE_COL_W;
            double dy = y + (i % PE_COL_MAX) * PE_ROW_H;

            String label = ProtectionEquipmentStyleCatalog.getLabel(pe.typ(), active);
            String color = ProtectionEquipmentStyleCatalog.getColor(pe.typ(), active);

            Map<String, String> metadataMap = new HashMap<>();
            metadataMap.put("libelle", pe.libelle());
            metadataMap.put("tase2", pe.tase2());
            metadataMap.put("tase2_control", pe.tase2_control());
            metadataMap.put("value", pe.value().toString());
            String metadata;
            try {
                metadata = MAPPER.writeValueAsString(metadataMap);
            } catch (JsonProcessingException e) {
                throw new AssertionError(e);  // Unreachable
            }

            nodeLabels.add(new NodeLabel(
                label,
                new LabelPosition("PE_" + color + "_" + i, dx, dy, false, 0),
                metadata
            ));
        }
    }

    // The terminal whose bay this feeder draws, or null when the feeder carries no bay of its own.
    private Terminal getFeederTerminal(FeederNode feederNode) {
        return switch (network.getIdentifiable(feederNode.getEquipmentId())) {
            case Branch<?> b when feederNode.getFeeder() instanceof FeederWithSides fws ->
                b.getTerminal(fws.getSide() == NodeSide.ONE ? TwoSides.ONE : TwoSides.TWO);
            case ThreeWindingsTransformer t when feederNode.getFeeder() instanceof FeederTwLeg leg ->
                getDrawnLegTerminal(t, leg);
            case Injection<?> inj -> inj.getTerminal();
            default -> null;
        };
    }

    // Return the terminal of the transformer leg being drawn, or null if the leg is not in the voltage
    // level currently being drawn (avoid repeating protections)
    private Terminal getDrawnLegTerminal(ThreeWindingsTransformer transformer, FeederTwLeg legNode) {
        String drawnVoltageLevelId = legNode.getOwnVoltageLevelInfos().id();
        ThreeSides nodeSide = ThreeSides.valueOf(legNode.getSide().getIntValue());
        ThreeSides drawnSide = null;
        ThreeSides firstOtherSide = null;
        int index = 0;
        for (ThreeWindingsTransformer.Leg leg : transformer.getLegs()) {
            ThreeSides side = ThreeSides.values()[index++];
            if (leg.getTerminal().getVoltageLevel().getId().equals(drawnVoltageLevelId)) {
                if (drawnSide == null || side == nodeSide) {
                    drawnSide = side;
                }
            } else if (firstOtherSide == null) {
                firstOtherSide = side;
            }
        }
        if (drawnSide == null || (nodeSide != drawnSide && nodeSide != firstOtherSide)) {
            return null;
        }
        return transformer.getTerminal(drawnSide);
    }

    private NodeSide getFeederSide(FeederNode feederNode, Terminal terminal) {
        if (network.getIdentifiable(feederNode.getEquipmentId()) instanceof ThreeWindingsTransformer t) {
            return NodeSide.valueOf(t.getSide(terminal).name());
        }
        return feederNode.getFeeder() instanceof FeederWithSides fws ? fws.getSide() : null;
    }

    private String getBreakerIdForFeeder(Terminal terminal) {
        if (terminal.getVoltageLevel().getTopologyKind() != TopologyKind.NODE_BREAKER) {
            // A bus breaker voltage level has no nodes to walk
            return null;
        }
        VoltageLevel.NodeBreakerView nbv = terminal.getVoltageLevel().getNodeBreakerView();
        int node = terminal.getNodeBreakerView().getNode();

        Set<Integer> visited = new HashSet<>();
        Queue<Integer> queue = new ArrayDeque<>();
        queue.add(node);
        visited.add(node);

        while (!queue.isEmpty()) {
            int current = queue.poll();
            for (Switch sw : nbv.getSwitches()) {
                int n1 = nbv.getNode1(sw.getId());
                int n2 = nbv.getNode2(sw.getId());
                if (n1 != current && n2 != current) continue;
                if (sw.getKind() == SwitchKind.BREAKER) return sw.getId();
                int next = n1 == current ? n2 : n1;
                if (visited.add(next)) queue.add(next);
            }
            // A merged three windings transformer hangs off its bay by an internal connection, so the
            // walk has to cross those too or it stops on the leg itself.
            for (VoltageLevel.NodeBreakerView.InternalConnection ic : nbv.getInternalConnections()) {
                int n1 = ic.getNode1();
                int n2 = ic.getNode2();
                if (n1 != current && n2 != current) continue;
                int next = n1 == current ? n2 : n1;
                if (visited.add(next)) queue.add(next);
            }
        }
        return null;
    }
}
