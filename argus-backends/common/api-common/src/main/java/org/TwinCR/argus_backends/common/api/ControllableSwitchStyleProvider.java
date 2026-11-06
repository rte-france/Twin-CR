/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.api;

import java.util.List;

import java.util.Set;

import com.powsybl.sld.model.nodes.SwitchNode;
import com.powsybl.sld.svg.styles.StyleProvider;

import com.powsybl.sld.library.SldComponentLibrary;
import com.powsybl.sld.model.cells.Cell;
import com.powsybl.sld.model.graphs.Graph;
import com.powsybl.sld.model.graphs.VoltageLevelGraph;
import com.powsybl.sld.model.nodes.BranchEdge;
import com.powsybl.sld.model.nodes.Edge;
import com.powsybl.sld.model.nodes.Node;
import com.powsybl.sld.svg.BusInfo;
import com.powsybl.sld.svg.BusLegendInfo;
import com.powsybl.sld.svg.FeederInfo;
import com.powsybl.sld.svg.LabelProvider;


public class ControllableSwitchStyleProvider implements StyleProvider {

    private final Set<String> controllableSwitchIds;

    public ControllableSwitchStyleProvider(Set<String> controllableSwitchIds) {
        this.controllableSwitchIds = Set.copyOf(controllableSwitchIds);
    }

    @Override
    public List<String> getNodeStyles(VoltageLevelGraph graph, Node node, SldComponentLibrary componentLibrary, boolean showInternalNodes) {
        if (node instanceof SwitchNode switchNode
                && !controllableSwitchIds.contains(switchNode.getEquipmentId())) {
            return List.of("sld-fictitious");
        }
        return List.of();
    }

    @Override public List<String> getEdgeStyles(Graph graph, Edge edge) { return List.of(); }
    @Override public List<String> getNodeDecoratorStyles(LabelProvider.NodeDecorator nodeDecorator, Node node, SldComponentLibrary componentLibrary) { return List.of(); }
    @Override public List<String> getBranchEdgeStyles(BranchEdge edge, SldComponentLibrary componentLibrary) { return List.of(); }
    @Override public List<String> getNodeSubcomponentStyles(Graph graph, Node node, String subComponentName) { return List.of(); }
    @Override public List<String> getCssFilenames() { return List.of(); }
    @Override public List<String> getBusStyles(String busId, VoltageLevelGraph graph) { return List.of(); }
    @Override public List<String> getBusInfoStyle(BusInfo info) { return List.of(); }
    @Override public List<String> getBusLegendCaptionStyles(BusLegendInfo.Caption caption) { return List.of(); }
    @Override public List<String> getFeederInfoStyles(FeederInfo info) { return List.of(); }
    @Override public List<String> getCellStyles(Cell cell) { return List.of(); }
    @Override public void reset() {}
}
