# Temporary config (to be fixed)

## To be added to the argus-backends directory.
These files must be added before building the "private" variant of the argus-backend images (see [Build variants](#build-variants)). They are not required for the "public" variant, which builds without state estimation.
* estim-V6.9.2.6-linux.tar.gz
* jars-powsybl-rte-5.5.0.tar

They are RTE private files, documented in the RTE-internal documentation (not published).

## Jetstream
For now, jetstream must be enabled in the nats server.
TODO: jetstream should not be necessary.



# Twin-CR Argus Backend

The Argus Backend is a core component of the Twin-CR project. It is responsible for consuming telemetry from NATS, updating a real-time grid model based on PowSyBl, running state estimations, and managing alarms.

## Features

- **Telemetry Consumption**: Real-time consumption of TM (Telemetry) and TS (Telesignaling) from NATS.
- **Grid Modeling**: Integration with [PowSyBl](https://www.powsybl.org/) for managing IIDM grid models.
- **State Estimation**: Built-in support for running state estimations via PowSyBl (requires the private [build variant](#build-variants))
- **Alarm Engine**: Rule-based alarm evaluation and publishing.
- **HTTP API**: REST API for monitoring health, alarms, and triggering estimations.
- **Command Handling**: Request-Reply pattern for handling external commands.
- **Flexible Configuration**: Supports CLI arguments, environment variables, and system properties.

There are 2 versions of the backend component: the gamemaster (gm) version which has access to all physical values from the orchestrator and updates its grid model based on those, and the SCADA version which updates its grid model based on TM's and TS's and complete them using a state estimation.

## Project Structure

The project is structured as a multi-module Maven project:

- `common`: Common sources between the gm and SCADA version
- `gm`: Game master version
- `scada`: SCADA version
- `utils`: Shared utility tools.

The `common`, `gm`, and `scada` folders all have the same structure containing
- `bootstrap`: Entry point of the application (`Main` class).
- `core`: Core configuration, NATS connection factory, and shared utilities.
- `model`: Grid model management and TASE.2 mapping logic.
- `telemetry`: NATS telemetry consumer and stream initialization.
- `alarms`: Alarm engine, repository, and publisher.
- `api`: Embedded HTTP server providing a REST API.
- `commands`: Handler for command requests.

`scada` additionally contains `estim-rte`: the RTE-private state estimation implementation, built only for the [private variant](#build-variants). It implements `utils`'s `StateEstimationProvider` SPI and is discovered at runtime via `ServiceLoader`; when it is absent from the classpath, state estimation is simply skipped.

## Prerequisites

- Java 21
- Maven 3.8+
- A running NATS server

## Installation

### Build variants

argus-backends can be built in two variants:

- **private** (default): full features, including state estimation. Requires the private powsybl-rte jars and the estim binary, and builds the `scada/estim-rte` module.
- **public**: builds without any private dependency, state estimation is skipped.


For the private version, see ([docker-compose-argus-backends.yaml](../docker-compose-argus-backends.yaml)) on how to install private dependencies, then run

```bash
mvn clean install
```

To build the public variant, simply:
```bash
mvn clean install -Dpublic.build=true
```

### Building behind a corporate proxy

Using Maven inside a Dockerfile behind a corporate proxy typically fails because Maven cannot resolve external dependencies or reach Maven Central through the network barrier.

Resolving this requires configuring both Docker build arguments and Maven's settings.xml inside the container. If your corporate proxy performs SSL inspection, you will also need to handle custom certificates.

To handle this, optional scripts can be added to the `argus-backends` folder and invoked during the build:
- `set_mvn_opts.sh`: configures Maven with your proxy settings (e.g., generates `/root/.m2/settings.xml` with the appropriate configuration).
- `unset_mvn_opts.sh`: cleans up the configuration after the build step (e.g., removes `/root/.m2/settings.xml`).

Both scripts must be executable (`chmod +x`): a missing or non-executable script is silently skipped.

## Usage

### Main module (argus-backends-bootstrap)
The backend can be run either using docker compose ([docker-compose-argus-backends.yaml](../docker-compose-argus-backends.yaml)) or via

```bash
# GM backend
java -jar gm/bootstrap-gm/target/bootstrap-gm-5.5.0.jar --http-port=8083 --config-path=<config file (config.toml)>
# SCADA backend
java -jar scada/bootstrap-scada/target/bootstrap-scada-5.5.0.jar --http-port=8082 --config-path=<config file (config.toml)> --grid-model-path=<grid model file.arc.xz> --ti-mapping-path=<mapping file (timapped.json.xz)>
```

#### Command Line Options

Common options

| Option | Description | Default |
|--------|-------------|---------|
| `--nats-url` | NATS server URL | `nats://localhost:4222` |
| `--http-port` | HTTP API port | |
| `--config-path` | Path to the main config.toml (CLICKHOUSE mode only) | |
| `--iidm-version` | IIDM version used when writing network case | `1.14` |
| `--mode` | Whether file are fetched from the FILESYSTEM or CLICKHOUSE | `FILESYSTEM` |
| `--clichouse-host` | Hostname for Clickhouse (CLICKHOUSE mode only) | `localhost` |
| `--clichouse-port` | Port for Clickhouse (CLICKHOUSE mode only) | `8123` |
| `--configurator-host` | Hostname for the Configurator (CLICKHOUSE mode only) | `localhost` |
| `--configurator-port` | Port for the Configurator (CLICKHOUSE mode only) | `8080` |
| `--help` | Show help message | |
| `--version` | Show version information | |

GM-specific options

| Option | Description | Default |
|--------|-------------|---------|
| N/A | N/A | N/A |

SCADA-specific options

| Option | Description | Default |
|--------|-------------|---------|
| `--estim-period` | Time interval between periodic runs of the state estimator in seconds | 60 |
| `--stale-measurement-timeout` | Time in seconds after which a measurement not refreshed is considered stale/is displayed in blue | 30 |

### API Endpoints

Once started, the API is available at `http://localhost:<port>`. The API documentation is available at `http://localhost:<port>/swagger-ui`.

### Utility modules
The `utils` module contains various utilities.

```bash
java -cp scada/bootstrap-scada/target/bootstrap-scada-5.5.0.jar com.powsybl.tools.Main [OPTIONS]
[main] INFO com.powsybl.commons.config.PlatformConfig - Using platform configuration provider classic
[main] INFO com.powsybl.commons.config.PlatformConfig - Platform configuration defined by YAML file /home/<user>/.itools/config.yml
[main] INFO com.powsybl.computation.DefaultComputationManagerConfig - DefaultComputationManagerConfig(shortTimeExecutionComputationManagerFactoryClass=com.powsybl.computation.local.LocalComputationManagerFactory, longTimeExecutionComputationManagerFactoryClass=com.powsybl.computation.local.LocalComputationManagerFactory)
usage: itools [OPTIONS] COMMAND [ARGS]

Available options are:
    --config-name <CONFIG_NAME>   Override configuration file name

Available commands are:

Computation:
    cmpmeas                                  Compare measurements of two cases
    compare-security-analysis-results        Compare security analysis results
    estim                                    Run state estimation
    loadflow                                 Run loadflow
    loadflow-validation                      Validate load-flow results of a network
    security-analysis                        Run security analysis
    sensitivity-analysis                     Run sensitivity analysis
    shortcircuit                             Run short circuit analysis
    showinjs                                 Show synthetic injection information

Data conversion:
    convert-network                          convert a network from one format to another

Data preprocessing and case conversion:
    arc2xml                                  Convert the given arcade binary network to an arcade xml one
    casecheck                                Check case consistency on 'some aspects'
    casecompare                              Case comparison on 'some aspects'

Misc:
    generate-completion-script               Generates a bash autocompletion script
    plugins-info                             List the available plugins

Single line diagram:
    generate-substation-diagram              generate substation diagram

Visualisation:
    sld                                      Build substation's SVG
```

## License

Copyright (c) 2025-2026, All partners of the Twin-CR project.
