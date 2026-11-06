/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.scada.gridmodel;

import com.fasterxml.jackson.databind.MappingIterator;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.powsybl.commons.extensions.Extendable;
import com.powsybl.iidm.network.Branch;
import com.powsybl.iidm.network.Bus;
import com.powsybl.iidm.network.Connectable;
import com.powsybl.iidm.network.Identifiable;
import com.powsybl.iidm.network.Injection;
import com.powsybl.iidm.network.Terminal;
import com.powsybl.iidm.network.ThreeSides;
import com.powsybl.iidm.network.ThreeWindingsTransformer;
import com.powsybl.iidm.network.extensions.DiscreteMeasurement;
import com.powsybl.iidm.network.extensions.DiscreteMeasurements;
import com.powsybl.iidm.network.extensions.Measurement;
import com.powsybl.iidm.network.extensions.MeasurementAdder;
import com.powsybl.iidm.network.extensions.Measurements;
import com.powsybl.iidm.network.extensions.MeasurementsAdder;

import org.TwinCR.argus_backends.common.core.util.FileLoader;
import org.TwinCR.argus_backends.common.core.util.PooledString;
import org.TwinCR.argus_backends.common.gridmodel.GridModel;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class TiMapping {
    private static final Logger LOGGER = LoggerFactory.getLogger(TiMapping.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    public static Map<String, Ti> mapTase2_2_TI = new HashMap<>();
    public static Map<String, Ti> mapId_2_Output = new HashMap<>();
    public static Map<String, Measurement> libelle2Measurement = new HashMap<>();
    public static Set<String> initiallyInvalidMeasurements = new HashSet<>();
    public static Map<String, DiscreteMeasurement> libelle2DiscreteMeasurement = new HashMap<>();

    public static void buildMeasurementsMap() {
        for (Connectable<?> obj: GridModel.network.getConnectables()) {
            if (obj != null) {
                Measurements<?> ms = (Measurements<?>) obj.getExtension(Measurements.class);
                if (ms != null) {
                    for (Measurement m : (Iterable<Measurement>) ms.getMeasurements()) {
                        libelle2Measurement.put(m.getId(), m);
                        if (!m.isValid()) {
                            initiallyInvalidMeasurements.add(m.getId());
                        }
                    }
                }
            }
        }
    }

    public static void buildDiscreteMeasurementsMap() {
        for (Identifiable<?> obj: GridModel.network.getIdentifiables()) {
            if (obj != null) {
                DiscreteMeasurements<?> ms = (DiscreteMeasurements<?>) obj.getExtension(DiscreteMeasurements.class);
                if (ms != null) {
                    for (DiscreteMeasurement m : (Iterable<DiscreteMeasurement>) ms.getDiscreteMeasurements()) {
                        libelle2DiscreteMeasurement.put(m.getId(), m);
                    }
                }
            }
        }
    }

    public static void load(Path name) {
        // Load an eventually compressed timapped.json
        List<Ti> entries = parse(name);

        // Measurement and discreteMeasurement extensions
        buildMeasurementsMap();
        buildDiscreteMeasurementsMap();
        if (libelle2Measurement.size() == 0 && libelle2DiscreteMeasurement.size() == 0) {
            LOGGER.warn("Network has no measurement extensions, adding fake measurements to all elements");
            addMeasurements(entries);
            buildMeasurementsMap();
            buildDiscreteMeasurementsMap();
        }

        LOGGER.info("=== Measurements: {} measurements", libelle2Measurement.size());
        for (Map.Entry<String, Measurement> m : libelle2Measurement.entrySet()) {
            LOGGER.debug("{} -> {}", m.getKey(), m.getValue().getId());
        }
        LOGGER.info("=== DiscreteMeasurements: {} discrete measurements", libelle2DiscreteMeasurement.size());
        for (Map.Entry<String, DiscreteMeasurement> m : libelle2DiscreteMeasurement.entrySet()) {
            LOGGER.debug("{} -> {}", m.getKey(), m.getValue().getId());
        }

        // tase2 to TI mapping
        int nbNok = 0, nbNokOM = 0;
        for (Ti item : entries) {
            if (item.tase2() != null) {
                // Telemeasurement
                mapTase2_2_TI.put(item.tase2(), item);
            } else {
                nbNok++;
                if ("OM".equals(item.type())) {
                    nbNokOM++;
                }
                if (item.id() != null) {
                    // Legacy format
                    mapId_2_Output.put(item.id(), item);
                }
            }
        }
        LOGGER.info("{} TI without a tase2 field (of which {} OM)", nbNok, nbNokOM);
    }

    private static List<Ti> parse(Path name) {
        List<Ti> entries = new ArrayList<>();
        try (InputStream in = FileLoader.open(name); MappingIterator<Ti> iterator = MAPPER.readerFor(Ti.class).readValues(in)) {
            // Iterate over the input stream instead of parsing the whole file at once for memory
            while (iterator.hasNext()) {
                entries.add(iterator.next());
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to parse JSON mapping file " + name, e);
        } finally {
            PooledString.release();
        }
        return entries;
    }

    private static void addMeasurements(List<Ti> scadaOutputs) {
        for (Ti scadaOutput : scadaOutputs) {
            String id = scadaOutput.id();
            String equipmentId = scadaOutput.equipmentId();
            String kind = scadaOutput.kind();
            if (id == null || equipmentId == null || kind == null) {
                LOGGER.warn("Addition of fake measurements only works on the legacy format (when no tase mapping is included)");
                return;
            }

            String side = scadaOutput.side();

            Identifiable<?> identifiable = GridModel.network.getIdentifiable(equipmentId);

            if (!(identifiable instanceof Extendable<?> extendable) || !(identifiable instanceof Connectable<?>)) {
                continue;
            }

            Measurements<?> measurements = (Measurements<?>) extendable.getExtension(Measurements.class);
            if (measurements == null) {
                measurements = (Measurements<?>) extendable.newExtension(MeasurementsAdder.class).add();
            }

            if (identifiable instanceof Branch<?> branch) {
                if (side == null) {
                    LOGGER.warn("Side must be specified for branch elements: {}", scadaOutput);
                } else if (side.equals("ONE")) {
                    addTerminalMeasurement(measurements, id, kind, branch.getTerminal1(), ThreeSides.ONE);
                } else if (side.equals("TWO")) {
                    addTerminalMeasurement(measurements, id, kind, branch.getTerminal2(), ThreeSides.TWO);
                }

            } else if (identifiable instanceof ThreeWindingsTransformer t3) {
                if (side == null) {
                    LOGGER.warn("Side must be specified for 3w-transformer elements: {}", scadaOutput);
                } else if (side.equals("ONE")) {
                    addTerminalMeasurement(measurements, id, kind, t3.getLeg1().getTerminal(), ThreeSides.ONE);
                } else if (side.equals("TWO")) {
                    addTerminalMeasurement(measurements, id, kind, t3.getLeg2().getTerminal(), ThreeSides.TWO);
                } else if (side.equals("THREE")) {
                    addTerminalMeasurement(measurements, id, kind, t3.getLeg3().getTerminal(), ThreeSides.THREE);
                }

            } else if (identifiable instanceof Injection<?> injection) {
                addTerminalMeasurement(measurements, id, kind, injection.getTerminal(), null);
            }
        }
    }
    private static void addTerminalMeasurement(
            Measurements<?> measurements,
            String id,
            String kind,
            Terminal terminal,
            ThreeSides side) {

        double p = terminal.getP();
        double q = terminal.getQ();

        Bus bus = terminal.getBusView().getBus();
        double v = bus != null ? bus.getV() : Double.NaN;

        if (kind.equals("P")) {
            addMeasurement(measurements, id, Measurement.Type.ACTIVE_POWER, p, side);
        } else if (kind.equals("Q")) {
            addMeasurement(measurements, id, Measurement.Type.REACTIVE_POWER, q, side);
        } else if (kind.equals("U")) {
            addMeasurement(measurements, id, Measurement.Type.VOLTAGE, v, side);
        }
    }

    private static void addMeasurement(
            Measurements<?> measurements,
            String id,
            Measurement.Type type,
            double value,
            ThreeSides side) {

        boolean valid = !Double.isNaN(value);

        MeasurementAdder adder = measurements.newMeasurement()
                .setId(id)
                .setType(type)
                .setValue(value)
                .setStandardDeviation(0.0)
                .setValid(valid)
                .putProperty("validity", valid ? "0" : "1");

        if (side != null) {
            adder.setSide(side);
        }

        adder.add();
    }
}
