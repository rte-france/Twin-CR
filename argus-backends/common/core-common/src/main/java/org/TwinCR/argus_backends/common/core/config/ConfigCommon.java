/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.core.config;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.tomlj.Toml;
import org.tomlj.TomlParseResult;

import picocli.CommandLine;
import picocli.CommandLine.Command;
import picocli.CommandLine.Option;

@Command(name = "common-backend", mixinStandardHelpOptions = true, version = "5.2.0",
        description = "Common parameters for SCADA and GameMaster backends for Twin-CR")
public class ConfigCommon implements Runnable {
    private static final Logger LOGGER = LoggerFactory.getLogger(ConfigCommon.class);
    @Option(names = {"--nats-url"}, description = "NATS server URL", defaultValue = "nats://localhost:4222")
    protected String natsUrl;

    @Option(names = {"--http-port"}, description = "HTTP API port", required = true)
    protected int httpPort;

    @Option(names = {"--config-path"}, description = "Path to the configuration TOML file")
    private String configPath;

    @Option(names = {"--iidm-version"}, description = "IIDM version used when writing network case", defaultValue = "1.14")
    private String iidmVersion;

    public String iidmVersion() {
        return iidmVersion;
    }

    public String natsUrl() {
        return natsUrl;
    }

    public int httpPort() {
        return httpPort;
    }

    @Option(names = {"--mode"}, description = "Source of input files: FILESYSTEM or CLICKHOUSE", defaultValue = "FILESYSTEM")
    protected InputSource inputSource;

    public enum InputSource {
        FILESYSTEM,
        CLICKHOUSE
    }
    public InputSource getInputSource() { return inputSource; }

    @Option(names = "--clickhouse-host", defaultValue = "localhost")
    protected String clickhouseHost;

    @Option(names = "--clickhouse-port", defaultValue = "8123")
    protected int clickhousePort;

    @Option(names = "--configurator-host", defaultValue = "localhost")
    protected String configuratorHost;

    @Option(names = "--configurator-port", defaultValue = "8080")
    protected int configuratorPort;

    private String cachedSimulationId;
    private String simulationId() {
        if (cachedSimulationId == null) {
            ConfiguratorClient configurator = new ConfiguratorClient(configuratorHost, configuratorPort);
            cachedSimulationId = configurator.getSimulationId();
        }
        return cachedSimulationId;
    }

    private String cachedConfigPath;
    public String configPath() {
        if (inputSource == InputSource.FILESYSTEM) {
            return configPath;
        } else {
            if (cachedConfigPath == null) {
                ConfiguratorClient configurator = new ConfiguratorClient(configuratorHost, configuratorPort);
                cachedConfigPath = configurator.getConfigPath();
            }
            return cachedConfigPath;
        }
    }

    public Path gridModelPath() {
        return getPathFromConfig("iidm_file");
    }

    public Path tiMappingPath() {
        try {
            return getPathFromConfig("scada_backend.mapping_file");
        } catch (IllegalStateException e) {
            LOGGER.warn("No input_file.scada_backend.mapping_file specified in TOML, using input_file.scada_outputs_file instead");
            return getPathFromConfig("scada_outputs_file");
        }
    }

    public Path GmControlsPath() {
        return getPathFromConfig("game_master_inputs_file");
    }

    public Path IflConfigPath() {
        return getPathFromConfig("cyber_config_file");
    }

    public Optional<Path> geoDataPath() {
        try {
            return Optional.of(getPathFromConfig("geo_data"));
        } catch (IllegalStateException e) {
            return Optional.empty();
        }
    }

    public Optional<String> synopticsDir() {
        return Optional.ofNullable(config().getString("input_files.argus.synoptics_dir"));
    }

    // Resolve a path relative to the config.toml (FILESYSTEM) or materialize it from ClickHouse (CLICKHOUSE)
    public Path resolveInputFile(String relPath) {
        if (inputSource == InputSource.FILESYSTEM) {
            return resolveLocalPath(relPath);
        }
        return materializeFromClickHouse(relPath);
    }

    public Optional<Path> cycosimConfigPath() {
        try {
            return Optional.of(getPathFromConfig("cycosim_integration_file"));
        } catch (IllegalStateException e) {
            return Optional.empty();
        }
    }

    @Override
    public void run() {
        if (inputSource == InputSource.FILESYSTEM && configPath == null) {
            throw new CommandLine.ParameterException(new CommandLine(this), "--config-path is required when --mode=FILESYSTEM");
        }
    }

    protected Path getPathFromConfig(String file) throws IllegalStateException {
        TomlParseResult config = config();
        String relPath = config.getString("input_files." + file);
        if (relPath == null) {
            throw new IllegalStateException("Missing 'input_files." + file + "' in config");
        }
        return resolveInputFile(relPath);
    }

    // Resolve path given from the config.toml file
    private Path resolveLocalPath(String relPath) {
        Path configFilePath = Paths.get(configPath).toAbsolutePath().normalize();
        Path path = Paths.get(relPath);

        if (!path.isAbsolute()) {
            path = configFilePath.getParent().resolve(path);
        }
        return path.toAbsolutePath().normalize();
    }

    // Get file content from clickhouse, write it to a temp file and return the Path of the temp file
    private Path materializeFromClickHouse(String path) {
        String simulationId = simulationId();
        ClickhouseClientWrapper service = new ClickhouseClientWrapper(clickhouseHost, clickhousePort, simulationId);

        byte[] content = service.getFileContent(path);

        try {
            String prefix;
            String suffix;

            int dot = path.indexOf('.');
            if (dot == -1) {
                prefix = path;
                suffix = "";
            } else {
                prefix = path.substring(0, dot);
                suffix = path.substring(dot);  // Preserve extension for compression/format detection
            }

            Path prefixPath = Path.of(prefix);
            Path parent = prefixPath.getParent();

            Path baseTemp = Path.of(System.getProperty("java.io.tmpdir"));
            Path subDir = (parent != null)
                ? baseTemp.resolve(parent)
                : baseTemp;
            Files.createDirectories(subDir);

            Path filePrefix = prefixPath.getFileName();
            Path tempFile = Files.createTempFile(subDir, filePrefix + "_", suffix);
            Files.write(tempFile, content);
            tempFile.toFile().deleteOnExit();
            LOGGER.info("Writing temp file {}", tempFile.toAbsolutePath());
            return tempFile.toAbsolutePath();

        } catch (IOException e) {
            throw new IllegalStateException("Failed to materialize ClickHouse file: " + path, e);
        }
    }

    public double period() {
        TomlParseResult config = config();
        Object raw = config.get("master.period");
        if (raw == null) {
            throw new IllegalStateException("Missing required configuration value: master.period");
        }
        if (!(raw instanceof Number)) {
            throw new IllegalStateException("master.period must be numeric");
        }

        return ((Number) raw).doubleValue();
    }

    private Path cachedTomlPath;
    protected TomlParseResult config() {
        Path tomlPath;
        if (inputSource == InputSource.FILESYSTEM) {
            tomlPath = Paths.get(configPath());
        } else {
            if (cachedTomlPath == null) {
                tomlPath = materializeFromClickHouse(Paths.get(configPath()).getFileName().toString());
                cachedTomlPath = tomlPath;
            } else {
                tomlPath = cachedTomlPath;
            }
        }

        TomlParseResult result;
        try {
            result = Toml.parse(tomlPath);
        } catch (IOException e) {
            throw new IllegalStateException("Failed to read config file: " + tomlPath, e);
        }

        if (result.hasErrors()) {
            throw new IllegalStateException("Invalid TOML configuration: " + result.errors());
        }
        return result;
    }
}
