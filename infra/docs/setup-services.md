# Setup TwinEU services

*This document outlines the internal components of a TwinEU session and provides the operational commands to build and publish their container images.*


## Image Build & Registry Push

The following commands build the Docker images for all custom components and push them to the internal TwinEU registry (`registry.twin.eu`).

```bash
# 1. Load pre-built SCADA base image if required
docker load -i /tmp/scada.tar

# 2. Gamemaster API
docker build -t registry.twin.eu/gamemaster:latest -f envs/Dockerfile.gamemaster .
docker push registry.twin.eu/gamemaster:latest

# 3. TwinEU-Core Orchestrator
docker build -t registry.twin.eu/twineu-core:latest -f envs/Dockerfile.orchestrator .
docker push registry.twin.eu/twineu-core:latest

# 4. Configurator Client
docker build -t registry.twin.eu/configurator-client:latest -f configurator_client/Dockerfile-no-uv configurator_client/
docker push registry.twin.eu/configurator-client:latest

# 5. Automata Worker
docker build -t registry.twin.eu/automata:latest -f envs/Dockerfile.automata .
docker push registry.twin.eu/automata:latest

# 6. Argus Backends
docker build --target scada -t registry.twin.eu/argus-scada:latest -f argus-backends/Dockerfile.argus-backends argus-backends/
docker push registry.twin.eu/argus-scada:latest

docker build --target gm -t registry.twin.eu/argus-gm:latest -f argus-backends/Dockerfile.argus-backends argus-backends/
docker push registry.twin.eu/argus-gm:latest
