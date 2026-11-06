/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.gridmodel;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.MappingIterator;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;

import com.powsybl.iidm.network.BusbarSection;
import com.powsybl.iidm.network.Network;
import com.powsybl.iidm.network.SwitchKind;
import com.powsybl.iidm.network.VoltageLevel;
import com.powsybl.math.graph.TraverseResult;

import org.TwinCR.argus_backends.common.core.util.FileLoader;
import org.TwinCR.argus_backends.common.core.util.PooledString;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.Set;

// The TI mapping declares ground disconnectors that the IIDM case does not contain, so they are added here at load time
public final class GroundDisconnectors {
    private static final Logger LOGGER = LoggerFactory.getLogger(GroundDisconnectors.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();
    private static final String BAY_TYPE = "GroundDisconnector";
    private static final Set<String> SIMULATED_TYPES = Set.of("TS", "OM");

    @JsonIgnoreProperties(ignoreUnknown = true)
    private record TiMappedEntry(
        @JsonProperty("type")    @JsonDeserialize(using = PooledString.class) String type,
        @JsonProperty("libelle") String libelle,
        @JsonProperty("bayt")    @JsonDeserialize(using = PooledString.class) String bayt,
        @JsonProperty("iidmdj")  @JsonDeserialize(using = PooledString.class) String iidmdj,
        @JsonProperty("bayiidm") @JsonDeserialize(using = PooledString.class) String bayiidm
    ) {}

    private GroundDisconnectors() {
    }

    public static void addTo(Network network, Path tiMappedPath) {
        int added = 0, noVoltageLevel = 0, noBreaker = 0, noFeederSide = 0, alreadyPresent = 0;

        try (InputStream in = FileLoader.open(tiMappedPath);
             MappingIterator<TiMappedEntry> iterator = MAPPER.readerFor(TiMappedEntry.class).readValues(in)) {
            while (iterator.hasNext()) {
                TiMappedEntry e = iterator.next();
                if (!BAY_TYPE.equals(e.bayt()) || !SIMULATED_TYPES.contains(e.type()) || e.libelle() == null) {
                    continue;
                }
                VoltageLevel vl = e.bayiidm() == null ? null : network.getVoltageLevel(e.bayiidm());
                if (vl == null) {
                    noVoltageLevel++;
                    continue;
                }
                String switchId = vl.getId() + "_" + e.libelle();
                if (network.getSwitch(switchId) != null) {
                    alreadyPresent++;
                    continue;
                }
                if (e.iidmdj() == null || network.getSwitch(e.iidmdj()) == null) {
                    noBreaker++;
                    continue;
                }
                int feederNode = feederSideNode(vl, e.iidmdj());
                if (feederNode < 0) {
                    noFeederSide++;
                    continue;
                }
                add(vl, switchId, e.libelle(), feederNode);
                added++;
            }
        } catch (IOException ex) {
            throw new RuntimeException("Failed to read ground disconnectors from " + tiMappedPath, ex);
        } finally {
            PooledString.release();
        }

        LOGGER.info("Added {} ground disconnectors ({} skipped: {} unknown voltage level, {} breaker not in the case, "
                + "{} breaker side undetermined, {} already in the case)",
                added, noVoltageLevel + noBreaker + noFeederSide + alreadyPresent,
                noVoltageLevel, noBreaker, noFeederSide, alreadyPresent);
    }

    private static void add(VoltageLevel vl, String switchId, String libelle, int feederNode) {
        VoltageLevel.NodeBreakerView nodeBreakerView = vl.getNodeBreakerView();
        int groundNode = nodeBreakerView.getMaximumNodeIndex() + 1;

        vl.newGround()
            .setId(switchId + "_GROUND")
            .setNode(groundNode)
            .add();
        nodeBreakerView.newSwitch()
            .setId(switchId)
            .setName(libelle)
            .setKind(SwitchKind.DISCONNECTOR)
            .setOpen(true)
            .setRetained(false)
            .setNode1(feederNode)
            .setNode2(groundNode)
            .add();
    }

    // Of the breaker's two nodes, the feeder side is the one from which no busbar section can be
    // reached without going back through the breaker. Returns -1 when neither or both qualify.
    private static int feederSideNode(VoltageLevel vl, String breakerId) {
        VoltageLevel.NodeBreakerView nodeBreakerView = vl.getNodeBreakerView();
        int node1 = nodeBreakerView.getNode1(breakerId);
        int node2 = nodeBreakerView.getNode2(breakerId);
        boolean busbarFrom1 = reachesBusbarSection(vl, node1, breakerId);
        boolean busbarFrom2 = reachesBusbarSection(vl, node2, breakerId);
        if (busbarFrom1 == busbarFrom2) {
            return -1;
        }
        return busbarFrom1 ? node2 : node1;
    }

    private static boolean reachesBusbarSection(VoltageLevel vl, int startNode, String excludedSwitchId) {
        VoltageLevel.NodeBreakerView nodeBreakerView = vl.getNodeBreakerView();
        if (isBusbarSection(vl, startNode)) {
            return true;
        }
        boolean[] found = {false};
        nodeBreakerView.traverse(startNode, (node1, sw, node2) -> {
            if (sw != null && sw.getId().equals(excludedSwitchId)) {
                return TraverseResult.TERMINATE_PATH;
            }
            if (isBusbarSection(vl, node2)) {
                found[0] = true;
                return TraverseResult.TERMINATE_TRAVERSER;
            }
            return TraverseResult.CONTINUE;
        });
        return found[0];
    }

    private static boolean isBusbarSection(VoltageLevel vl, int node) {
        return vl.getNodeBreakerView().getOptionalTerminal(node)
            .map(terminal -> terminal.getConnectable() instanceof BusbarSection)
            .orElse(false);
    }
}
