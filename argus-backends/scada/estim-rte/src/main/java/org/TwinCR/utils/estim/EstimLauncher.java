/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.utils.estim;

import com.powsybl.commons.datasource.*;
import com.powsybl.computation.ComputationManager;
import com.powsybl.computation.DefaultComputationManagerConfig;
import com.powsybl.computation.local.LocalComputationManager;
import com.powsybl.commons.datasource.DefaultDataSourceObserver;
import com.powsybl.iidm.network.*;
import com.powsybl.tools.ToolRunningContext;
import com.rte_france.powsybl.estim.EstimConfig;
import com.rte_france.powsybl.estim.EstimParameters;
import com.rte_france.powsybl.estim.EstimProvider;
import com.rte_france.powsybl.estim.EstimResult;
import com.rte_france.powsybl.estim.converter.EstimResultExporter;
import com.rte_france.powsybl.estim.converter.EstimResultExporters;
import org.apache.commons.lang3.tuple.ImmutablePair;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.io.Writer;
import java.nio.file.*;
import java.util.Map;
import java.util.HashMap;
import java.util.Properties;
import java.util.concurrent.atomic.AtomicReference;

/**
 *
 * @author Olivier Bretteville <olivier.bretteville at rte-france.com>
 */
public final class EstimLauncher implements StateEstimationProvider {
    private static final Logger LOGGER = LoggerFactory.getLogger(EstimLauncher.class);

    @Override
    public void runEstim(Network network) throws IOException, InterruptedException {
        launch(network, true);
    }

    public static void launch(Network network, boolean iidm, String inputFile, String outputFile, String outputFormat, String caseOutputFile, boolean compare, Exporter caseExporter, Properties exportProperties, ToolRunningContext context, String[] listesPostesIncompletementDecrits) throws IOException {
        LOGGER.info("Importing {} with raw data and measurements", inputFile);

        final Map<String, ImmutablePair<Double, Double>> bvSave = new HashMap<String, ImmutablePair<Double, Double>>();
        network.getBusBreakerView().getBusStream().forEach(bus ->  {
            if (compare) {
                bvSave.put(bus.getId(), new ImmutablePair<Double, Double>(bus.getAngle(), bus.getV()));
            }
            bus.setV(Double.NaN);
            bus.setAngle(Double.NaN);
        });

        ComputationManager computationManager = LocalComputationManager.getDefault();
        EstimConfig config = EstimConfig.fromPropertyFile();
        config.setLockOnWrite(false);
        EstimProvider provider = new EstimProvider(config);
        EstimResult result = provider.runAsync(network, computationManager, VariantManagerConstants.INITIAL_VARIANT_ID, EstimParameters.load())
                .join();

        // Estim results export
        if (outputFile != null) {
            DataSource ds2 = Exporters.createDataSource(context.getFileSystem().getPath(outputFile), new DefaultDataSourceObserver() {
                @Override
                public void opened(String streamName) {
                    context.getOutputStream().println("Generating file " + streamName + "...");
                }
            });
            String outputQuality = outputFile + ".quality.csv";
            try (Writer writer = Files.newBufferedWriter(context.getFileSystem().getPath(outputQuality))) {
                EstimResultExporter exporter = EstimResultExporters.getExporter(outputFormat, true);
                if (exporter != null) {
                    exporter.export(result, writer);
                } else {
                    System.err.println("No EstimResultExporter found");
                }
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
            String outputResults = outputFile + ".results.csv";
            try (Writer writer = Files.newBufferedWriter(context.getFileSystem().getPath(outputResults))) {
                EstimResultExporters.getExporter(outputFormat, false).export(result, writer);
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
            if (compare) {
                String compareResults = outputFile + ".compare.csv";
                try (Writer writer = Files.newBufferedWriter(context.getFileSystem().getPath(compareResults))) {
                    writer.write("bus,oldAngle,Angle,oldV,V,diffV,same\n");
                    network.getBusBreakerView().getBusStream().forEach(bus -> {
                        double oldAngle = bvSave.get(bus.getId()).getLeft();
                        double oldV = bvSave.get(bus.getId()).getRight();
                        double vDiff = Double.NaN;
                        if (!Double.isNaN(bus.getV()) && bus.getV() != 0.0) {
                            vDiff = 1.0 - (oldV / bus.getV());
                        }
                        try {
                            if ((oldV == bus.getV() || Double.isNaN(bus.getV()) && Double.isNaN(oldV)) && (oldAngle == bus.getAngle() || Double.isNaN(bus.getAngle()) && Double.isNaN(oldAngle))) {
                                writer.write(bus.getId() + "," + Double.toString(oldAngle) + "," + Double.toString(bus.getAngle()) + "," + Double.toString(oldV) + "," + Double.toString(bus.getV()) + "," + Double.toString(vDiff) + ",true\n");
                            } else {
                                writer.write(bus.getId() + "," + Double.toString(oldAngle) + "," + Double.toString(bus.getAngle()) + "," + Double.toString(oldV) + "," + Double.toString(bus.getV()) + "," + Double.toString(vDiff) + ",false\n");
                            }
                        } catch (IOException e) {
                            throw new UncheckedIOException(e);
                        }
                    });
                } catch (IOException e) {
                    throw new UncheckedIOException(e);
                }
            }

            if (outputFormat != null) {
                EstimResultExporters.export(result, context.getFileSystem().getPath(outputResults), outputFormat, false);
            }
            LOGGER.info("Estim metrics: {}", result.getMetrics());
        }

        // Case export
        if (caseOutputFile != null) {
            DataSource ds3 = Exporters.createDataSource(context.getFileSystem().getPath(caseOutputFile), new DefaultDataSourceObserver() {
                @Override
                public void opened(String streamName) {
                    context.getOutputStream().println("Generating case file " + streamName + "...");
                }
            });
            caseExporter.export(network, exportProperties, ds3);
        }
    }

    public static void launch(Network network, boolean lockOnWrite) throws IOException {
        ComputationManager computationManager = LocalComputationManager.getDefault();
        EstimConfig estimcfg = EstimConfig.fromPropertyFile();
        estimcfg.setLockOnWrite(lockOnWrite);
        EstimProvider provider = new EstimProvider(estimcfg);
        DefaultComputationManagerConfig config = DefaultComputationManagerConfig.load();
        ToolRunningContext context = new ToolRunningContext(System.out, System.err, FileSystems.getDefault(),
                config.createShortTimeExecutionComputationManager(), config.createLongTimeExecutionComputationManager());

        // Reset des phases et tension - TODO: à garder ?
        AtomicReference<Double> p0 = new AtomicReference<>(0.0), q0 = new AtomicReference<>(0.0);
        AtomicReference<Integer> nbFict = new AtomicReference<>(0);
        network.getBusBreakerView().getBusStream().forEach(bus ->  {
            bus.setV(Double.NaN);
            bus.setAngle(Double.NaN);
            if (bus.isFictitious()) {
                nbFict.set(nbFict.get() + 1);
                p0.set(p0.get()+bus.getFictitiousP0());
                q0.set(q0.get()+bus.getFictitiousQ0());
                bus.setFictitiousP0(0.0);
                bus.setFictitiousQ0(0.0);
            }
        });
        LOGGER.debug("Removed {} fictitious buses with a total active power of {} and a total reactive power of {}", nbFict.get(), p0.get(), q0.get());
        nbFict.set(0);
        p0.set(0.0);
        q0.set(0.0);
        network.getVoltageLevelStream().forEach(vl -> {
            if (vl.getTopologyKind() == TopologyKind.NODE_BREAKER) {
                for (int node : vl.getNodeBreakerView().getNodes()) {
                    if (vl.getNodeBreakerView().getFictitiousP0(node) != 0.0 || vl.getNodeBreakerView().getFictitiousQ0(node) != 0.0) {
                        nbFict.set(nbFict.get() + 1);
                        p0.set(p0.get()+vl.getNodeBreakerView().getFictitiousP0(node));
                        q0.set(q0.get()+vl.getNodeBreakerView().getFictitiousQ0(node));
                        vl.getNodeBreakerView().setFictitiousP0(node, 0.0);
                        vl.getNodeBreakerView().setFictitiousQ0(node, 0.0);
                    }
                }
            }
        });
        LOGGER.debug("Removed {} fictitious nodes with a total active power of {} and a total reactive power of {}", nbFict.get(), p0.get(), q0.get());

        EstimResult result = provider.runAsync(network, computationManager, VariantManagerConstants.INITIAL_VARIANT_ID, EstimParameters.load())
                .join();


        // Estim results export
        String outputFile = "estimOutput";
        String outputFormat = "CSV";

        if (outputFile != null) {
            DataSource ds2 = Exporters.createDataSource(context.getFileSystem().getPath(outputFile), new DefaultDataSourceObserver() {
                @Override
                public void opened(String streamName) {
                    context.getOutputStream().println("Generating file " + streamName + "...");
                }
            });
            String outputQuality = outputFile + ".quality.csv";
            try (Writer writer = Files.newBufferedWriter(context.getFileSystem().getPath(outputQuality))) {
                EstimResultExporter exporter = EstimResultExporters.getExporter(outputFormat, true);
                if (exporter != null) {
                    exporter.export(result, writer);
                } else {
                    System.err.println("No EstimResultExporter found");
                }
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }
            String outputResults = outputFile + ".results.csv";
            try (Writer writer = Files.newBufferedWriter(context.getFileSystem().getPath(outputResults))) {
                EstimResultExporter exporter = EstimResultExporters.getExporter(outputFormat, false);
                if (exporter != null) {
                    exporter.export(result, writer);
                } else {
                    System.err.println("No EstimResultExporter found");
                }
            } catch (IOException e) {
                throw new UncheckedIOException(e);
            }

            LOGGER.info("Estim metrics: {}", result.getMetrics());
        }
    }
}
