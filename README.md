# Twin-CR

Twin-CR is a platform for real-time cyber-physical co-simulation of power systems. It is primarily designed to serve as a digital twin or as a training platform for grid operators. Its primary features are:

- **SCADA-like interfaces**: Graphical interfaces for operators trainers and trainees to interact with the simulation in real-time.
- **Soft real-time simulation**: Runs in real-time (with ~1s precision) to allow exchanges with real operators and replica automaton.
- **Modular architecture**: Allowing for the easy integration of additional simulators or control loops.
- **DSL-based simulation configuration**: Definition of complex scenarios using a domain-specific language.
- **Scalability**: Tested on the whole French power system and its cyber infrastructure.

## Getting Started

The easiest way to start a simulation is through docker-compose. For this, first clone the repository

```bash
git clone https://github.com/rte-france/Twin-CR.git
cd Twin-CR
```

### Quick setup

`setup.sh` automatically setup your environment for an easy setup. It can be used both for fresh installs or when updating the repo. The main `setup.sh` options are

```bash
./setup.sh               # --help for the steps and options, e.g. --only env,dynawo or --skip build
./setup.sh --argus       # Linux only: also build the argus profile and the Argus AppImage
./setup.sh --rte         # RTE: private argus-backends and dynawo-rte (RTE private files, see the RTE-internal documentation, not published)
./setup.sh --skip build  # Skip building the docker images
./setup.sh --upload      # Also upload the examples to Garage (legacy: only needed without the lobby)
```

Note: `setup.sh` installs [mise](https://mise.jdx.dev) in `~/.local/bin` if needed (on Windows, [install it](https://mise.jdx.dev/installing-mise.html) yourself first), then the tools listed in `mise.toml` (Python, uv, Node, pnpm, jq, Go, pre-commit), and uses them; Docker is still to be installed separately. To also use these tools outside `setup.sh`, [activate mise](https://mise.jdx.dev/getting-started.html#activate-mise) in your shell.

Once setup, the platform can be launched with
```bash
docker compose build
docker compose up -d
# docker compose down -v  # To shutdown
```

### Environment files

The root `.env` is the only one used by docker compose. `setup.sh` generates one with sane defaults (based on `.env-example`), but you can update it manually if needed. Later `setup.sh` runs then warns you if your `.env` changes become obselete.

The service `.env` files (e.g. `session-manager/.env`) are only needed to run a service natively (`uv run ...`).

`python3 tools/env_sync.py check` (run by pre-commit and the CI) checks that every variable of a service `.env-example` is also in the root `.env-example`, with the same value, so that the containers receive it. When adding a variable to a service `.env-example`, either add it to the root `.env-example` too, or, if docker gets it another way (e.g. the compose `environment:`) or intentionally uses a different value (e.g. `localhost` natively vs the container name in docker), tag it with `[native]` in its inline comment:
```bash
CLICKHOUSE_HOST=localhost  # [native] in docker, taken from the root .env
DSL_SERVER_PORT=8000       # Same value natively and in docker: not tagged, kept in sync with the root .env-example
```

### Manual setup

Create a `.env` file in the project root using the `.env-example` and update it according to your needs
```bash
cp .env-example .env
```

The dev secrets (`GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN`, `GARAGE_METRICS_TOKEN`, `KEYCLOAK_ADMIN_PASSWORD`) are left empty in `.env-example` and docker compose refuses to start without them: `setup.sh` generates them (`./setup.sh --only secrets`), or generate each one with the command given next to it.

By default (MODE=CLICKHOUSE), simulation files are stored inside S3 using Garage. To connect, you will need to generate credentials and copy then to your `.env` as explained in [configurator_client/README.md](configurator_client/README.md).

If you wish the run the examples, you should first generate the associated mappings

```bash
cd docs/orchestrator/examples/4Bus
./cfg.sh

cd ../Nordic
./cfg.sh
```

Then upload them to S3 as explained in [configurator_client/README.md](configurator_client/README.md)

```bash
cd configurator_client
uv run upload_context ../docs/orchestrator/examples/Nordic/config.toml Nordic

uv run upload_context ../docs/orchestrator/examples/4Bus/config.toml 4Bus
uv run upload_context ../docs/orchestrator/examples/4Bus_PSCC/config.toml 4Bus_PSCC
```
This step only needs to be performed once (or when the examples are updated) as the data in S3 persist even after compose down (as long as your volumes still exists).

For more information regarding the examples and all input files, please refer to the orchestrator [documentation](docs/orchestrator/README.md). Additionally, the DSL language used to define scenarios is documented [here](docs/dsl_engine/DSL_Description.pdf).

Then, get [Dyna&omega;o] lastest release in the project releases.

Follow the instructions in [argus-backends/README.md](argus-backends/README.md) to build the Argus backends (required private data).

Finally, launch the platform with
```bash
docker compose build
docker compose up -d
# docker compose down -v  # To shutdown
```
The docker compose uses the network host mode, so on Windows and Mac, if you wish to connect services from the host machine to the docker services (e.g. to monitor the NATS server in the docker), you will need to enable host networking in Docker Desktop (Settings -> Resources -> Network -> Enable host networking -> Apply and restart). On Linux, this is enabled by default.

Multiple profiles can be used with the docker command:

### --profile=argus

Is the main profile and is used to launch the Game master and SCADA frontend (the backends are always started regardless of the profile used). Note that the argus frontend can also easily be launched natively with the following procedure :

1. Setup a .env variable as described in the argus/README.md file.
2. run :
```bash
cd argus
pnpm install
pnpm tauri dev
```

From this frontend, you can create a session (i.e. initialize a simulation) or join an existing session.

### --profile=hmi

Launches a simple mock frontend. It is mainly meant for dev use in MODE=FILESYSTEM. In MODE=CLICKHOUSE, a simulation must be started using the configurator_client api on http://localhost:8080/docs# before the mock frontend appears.

Note that when using this mock frontent, you might need to allow docker to show X11 windows
```bash
IP=$(ifconfig en0 | grep inet | awk '$1=="inet" {print $2}')
export DISPLAY=$IP:0
xhost +
```
On Mac, this requires installing XQuartz

## Explore

If you're new to the project, we recommend you to check the documentation, starting with:

1. This README
2. The main [ARCHITECTURE.md](docs/ARCHITECTURE.md) document describing all modules and how they interact
3. Finally, exploring the documentation of the individual modules based on your interests.
  - [Orchestrator](docs/orchestrator/README.md) - Interface between all modules and cyber modelling
  - [Argus](argus/README.md) - Game master and SCADA frontend
  - [Argus-backends](argus-backends/README.md) - Game master and SCADA backends
  - [DSL](docs/dsl_engine/DSL_Description.pdf) - Documentation for the domain-specific language used to defined scenarios
  - [DSL Engine](docs/game_master/README.md) - Documentation for the DSL server source code
  - [Configurator server](configurator_server/README.md)
  - [Configurator client](configurator_client/README.md)
  - [Session-manager](session-manager/README.md)
  - [Keycloak](keycloak/README.md)

When the docker compose is up, you can also check the Swagger API documentation of several services:
- Configurator client: http://localhost:8080/docs#/
- SCADA backend: http://localhost:8082/swagger-ui
- Game master backend: http://localhost:8083/swagger-ui
- DSL server: http://127.0.0.1:8000/docs
- Session-manager: http://localhost:8090/docs
And the DSL server source code documentation on: http://127.0.0.1:8000/redoc

## Running from source

For performance and/or development purposes, you might want to run the project or individual services outside Docker. However, note that this has only been tested on Ubuntu and Debian.

For the orchestrator and dependencies, please refer to the orchestrator-specific [documentation](docs/orchestrator/README.md)

For the legacy DSL server (the current one is now included in the Orchestrator)
```bash
pip install -r envs/requirements-rwth.txt
uvicorn gamemaster.app.main:app --reload
```

For argus

Setup a .env variable as described in the argus/README.md file.

Then :
```bash
cd argus
pnpm install
pnpm tauri dev
```

For the argus backends, please refer to the associated [documentation](argus-backends/README.md)

## Running Argus from AppImage

You can build Argus Appimage by running :
```bash
./envs/build_argus_AppImage.sh
```
Note that this operation takes time. Resulting appimage (`argus-debug.AppImage`, `argus-release.AppImage`) are placed in an `AppImage` directory.
Argus uses default URLs for some services, stored in a config.json file (by default, localhost is used). See argus/README.md.

## Running Argus on Windows

You can build Argus Windows executable by running :
```bash
./envs/build_argus_Windows.sh
```
Note that this operation takes time. Resulting exe (`argus-debug.exe`, `argus-release.exe`) are placed in a `Windows` directory.
Argus uses default URLs for some services, stored in a config.json file (by default, localhost is used). See argus/README.md.

## Multi machine setup

It is possible to run the services on one machine and to join a session from another machine.
In this case the joining machine need to add "twincr-server" in its /etc/hosts file with the ip address
of the machine running the service.

Example with address 10.11.12.13:
```bash
sudo sed -i.bak -E '/^[[:space:]]*[0-9a-fA-F.:]+[[:space:]]+twincr-server[[:space:]]*$/d' /etc/hosts  # Remove any previous twincr-server entry (useful when changing the mapping, e.g. to run Argus against a remote machine), alternatively, modify /etc/hosts by hand
echo "10.11.12.13 twincr-server" | sudo tee -a /etc/hosts
```

The setup should follow this structure:

            PC1                                                         PC2
    running : argus                                             running : global and session services, and argus
    /etc/hosts -> twincr-server 10.11.12.13                     IP : 10.11.12.13

PC2:
1. Start all services by running the docker-compose.yaml file with
    ```bash
    docker compose up
    or
    docker compose -f docker-compose.yaml up
    ```
2. Start argus with either the AppImage, or :
    ```bash
    cd argus
    pnpm tauri dev
    ```
PC1:

Start argus with either the AppImage, or :
```bash
cd argus
pnpm tauri dev
```

NB : The config.json used by Argus might have wrong URLs. You can modify it and restart Argus if needed. You will find it here : /home/<YOUR_USER>/.config/com.twincr.argus/config.json. The default one is at argus/src-tauri/config.json and is created if yours doesn't exist yet.

## Contributing

We welcome contributions to Twin-CR! To get started:

1. Open an issue
2. Create a feature branch (`git checkout -b #issue_number_feature`)
3. Install git pre-commit (`pip install pre-commit`) and set it up for this repo (`pre-commit install`)
4. Commit your changes (`git commit -s -m 'Add some amazing feature'`)
5. Push to the branch (`git push origin #issue_number_feature`)
6. Check all tests pass by running `pytest tests/nrt.py -vv -s 2>&1 | tee nrt.log` and update tests if needed
7. If you modified the behaviour of the Orchestrator DSLEngine, run and update the associated tests if needed (more info in the Orchestrator [README](docs/orchestrator/README.md)). Note: running those tests also updates the keyword list used by syntax highlighting.
8. Update documentation if needed
9. Open a pull request

## Testing

The main integration tests can be run with
```bash
python -m pip install -r requirements.txt
pytest tests/nrt.py -vv -s 2>&1 | tee tests/nrt.log
```

## Ports usage after docker rebinding

### Global

| **Service**     | **Port** | **Description** |
|-----------------|----------|-----------------|
| Garage / S3     | 3909     | Web UI          |
|                 | 3900     | S3 HTTP API     |
|                 | 3903     | S3 WEB API      |
| Session manager | 8090     | FastAPI server  |
| Keycloak        | 8443     | HTTP API        |

### Session

| **Service**             | **Port** | **Description** |
|-------------------------|----------|-----------------|
| Configurator client     | 8080     | Fast API server |
| Clickhouse              | 8123     | SQL API         |
| Gamemaster / DSL Server | 8000     | Fast API server |

## License

The source code of Twin-CR is licensed under the Mozilla Public License 2.0 (`MPL-2.0`). See the [LICENSE](LICENSE) file for the full text.

- Each source file starts with a license header that carries the `SPDX-License-Identifier: MPL-2.0` tag and refers to [AUTHORS.md](AUTHORS.md), which lists the copyright holder and the contributors.
- Third-party code, data and assets included in this repository are listed in [NOTICE](NOTICE), with their own license.
- `python3 licensing.py` adds or updates the headers of the tracked files. The `add-license-header` pre-commit hook runs it on the staged files.

