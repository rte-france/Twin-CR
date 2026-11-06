/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.telemetry;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import org.TwinCR.argus_backends.common.api.ClickhouseClient;
import org.TwinCR.argus_backends.common.api.EstimatedValue;
import org.TwinCR.argus_backends.common.api.EstimatedVariable;
import org.TwinCR.argus_backends.common.gridmodel.GridModel;
import org.TwinCR.utils.estim.EstimTool;
import org.TwinCR.utils.estim.StateEstimationProvider;
import org.TwinCR.utils.estim.StateEstimationProviders;
import org.apache.commons.lang3.tuple.Pair;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.powsybl.iidm.network.Battery;
import com.powsybl.iidm.network.Branch;
import com.powsybl.iidm.network.Bus;
import com.powsybl.iidm.network.Generator;
import com.powsybl.iidm.network.Injection;
import com.powsybl.iidm.network.Terminal;
import com.powsybl.iidm.network.ThreeWindingsTransformer;

public class StateEstimator {
    private static final Logger LOGGER = LoggerFactory.getLogger(StateEstimator.class);
    private static ClickhouseClient clickhouse = null;
    private static SseEstimatedValuesBridge bridge = null;

    public static void init(ClickhouseClient clickhouseClient, SseEstimatedValuesBridge bridge_) {
        clickhouse = clickhouseClient;
        bridge = bridge_;
    }

    public static void runEstim(double time) throws IOException, InterruptedException {
        Optional<StateEstimationProvider> provider = StateEstimationProviders.findProvider();
        if (provider.isEmpty()) {
            LOGGER.warn("No state estimation provider available on the classpath (public build without the private RTE jars?) - skipping estim");
            return;
        }

        long startTime = System.currentTimeMillis();
        LOGGER.info("Launching estim");
        Pair<Integer, Integer> nbcf = EstimTool.loadSynthesis(GridModel.network);
        LOGGER.debug("{} fictitious loads before estimation", nbcf);
        if (nbcf.getLeft() > 0 || nbcf.getRight() > 0) {
            LOGGER.debug("Deleting fictitious loads before estimation");
            synchronized (GridModel.network) {
                EstimTool.removeFictitiousLoads(GridModel.network);
            }
        }

        provider.get().runEstim(GridModel.network);
        LOGGER.info("Estim ran in {} ms", System.currentTimeMillis() - startTime);

        long startTime2 = System.currentTimeMillis();
        EstimTool.loadSynthesis(GridModel.network);
        LOGGER.info("{} fictitious loads after estimation (computed in {} ms)", nbcf, System.currentTimeMillis() - startTime2);

        startTime2 = System.currentTimeMillis();
        List<EstimatedValue> rows = collectEstimatedValues(time);
        clickhouse.insertEstimatedValues(rows);
        bridge.forward(rows);
        LOGGER.info("Published {} estimated values to Clickhouse in {} ms", rows.size(), System.currentTimeMillis() - startTime2);
        LOGGER.info("Overall time for runEstim: {} ms", System.currentTimeMillis() - startTime);
    }

    // List the variables that can be published by the state estimation. Same logic as collectEstimatedValues, but does not gather values/time
    public static List<EstimatedVariable> listVariables() {
        List<EstimatedVariable> vars = new ArrayList<>();

        GridModel.network.getIdentifiables().forEach(identifiable -> {
            if (identifiable instanceof Bus bus) {
                String topic = bus.getVoltageLevel().getSubstation().get().getId();
                vars.add(new EstimatedVariable(bus.getId(), "U",     Optional.empty(), topic));
                vars.add(new EstimatedVariable(bus.getId(), "angle", Optional.empty(), topic));

            } else if (identifiable instanceof ThreeWindingsTransformer twt) {
                String topic = twt.getLeg1().getTerminal().getVoltageLevel().getSubstation().get().getId();  // Same substation for all three legs
                vars.add(new EstimatedVariable(twt.getId(), "P", Optional.of("ONE"),   topic));
                vars.add(new EstimatedVariable(twt.getId(), "Q", Optional.of("ONE"),   topic));
                vars.add(new EstimatedVariable(twt.getId(), "P", Optional.of("TWO"),   topic));
                vars.add(new EstimatedVariable(twt.getId(), "Q", Optional.of("TWO"),   topic));
                vars.add(new EstimatedVariable(twt.getId(), "P", Optional.of("THREE"), topic));
                vars.add(new EstimatedVariable(twt.getId(), "Q", Optional.of("THREE"), topic));

            } else if (identifiable instanceof Branch<?> branch) {
                String topic1 = branch.getTerminal1().getVoltageLevel().getSubstation().get().getId();
                String topic2 = branch.getTerminal2().getVoltageLevel().getSubstation().get().getId();
                vars.add(new EstimatedVariable(branch.getId(), "P", Optional.of("ONE"), topic1));
                vars.add(new EstimatedVariable(branch.getId(), "Q", Optional.of("ONE"), topic1));
                vars.add(new EstimatedVariable(branch.getId(), "P", Optional.of("TWO"), topic2));
                vars.add(new EstimatedVariable(branch.getId(), "Q", Optional.of("TWO"), topic2));

            } else if (identifiable instanceof Injection<?> injection) {
                String topic = injection.getTerminal().getVoltageLevel().getSubstation().get().getId();
                vars.add(new EstimatedVariable(injection.getId(), "P", Optional.empty(), topic));
                vars.add(new EstimatedVariable(injection.getId(), "Q", Optional.empty(), topic));
            }
        });

        return vars;
    }

    private static List<EstimatedValue> collectEstimatedValues(double time) {
        List<EstimatedValue> rows = new ArrayList<>();

        synchronized (GridModel.network) {
            GridModel.network.getIdentifiables().forEach(identifiable -> {
                if (identifiable instanceof Bus bus) {
                    String topic = bus.getVoltageLevel().getSubstation().get().getId();
                    rows.add(new EstimatedValue(bus.getId(), "U",     Optional.empty(), nanToZero(bus.getV()),     time, topic));
                    rows.add(new EstimatedValue(bus.getId(), "angle", Optional.empty(), nanToZero(bus.getAngle()), time, topic));

                } else if (identifiable instanceof ThreeWindingsTransformer twt) {
                    addTerminalEstimates(rows, twt.getId(), "ONE",   twt.getLeg1().getTerminal(), 1.0, time);
                    addTerminalEstimates(rows, twt.getId(), "TWO",   twt.getLeg2().getTerminal(), 1.0, time);
                    addTerminalEstimates(rows, twt.getId(), "THREE", twt.getLeg3().getTerminal(), 1.0, time);

                } else if (identifiable instanceof Branch<?> branch) {
                    addTerminalEstimates(rows, branch.getId(), "ONE", branch.getTerminal1(), 1.0, time);
                    addTerminalEstimates(rows, branch.getId(), "TWO", branch.getTerminal2(), 1.0, time);

                } else if (identifiable instanceof Injection<?> injection) {
                    double sign = (injection instanceof Generator || injection instanceof Battery) ? -1.0 : 1.0;
                    addTerminalEstimates(rows, injection.getId(), null, injection.getTerminal(), sign, time);
                }
                // Substations, VoltageLevels, etc. are intentionally ignored
            });
        }

        return rows;
    }

    private static void addTerminalEstimates(List<EstimatedValue> rows, String id, String side, Terminal t, double sign, double time) {
        String topic = t.getVoltageLevel().getSubstation().get().getId();
        rows.add(new EstimatedValue(id, "P", Optional.ofNullable(side), sign * nanToZero(t.getP()), time, topic));
        rows.add(new EstimatedValue(id, "Q", Optional.ofNullable(side), sign * nanToZero(t.getQ()), time, topic));
    }

    private static double nanToZero(double v) {
        return Double.isNaN(v) ? 0.0 : v;
    }
}
