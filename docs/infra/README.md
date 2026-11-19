# Multi-session infrastructure (Nomad)

With docker compose, a machine runs one simulation session at a time. The Nomad infrastructure runs several: each
session is a Nomad job (`twincr-session.nomad.hcl`, in this folder) with its own NATS, ClickHouse, orchestrator,
configurator, Argus backends and automata, created and stopped by the session manager from Argus.

The services run the same images as with compose (their start and healthcheck scripts are baked in the images), so a
service behaves the same in both.

| | Compose | Nomad infrastructure |
|---|---|---|
| Sessions | one at a time, the services of `docker-compose-session.yaml` | one Nomad job per session |
| Global services | `docker-compose-global-services.yaml` | Nomad jobs: Keycloak, Garage, session manager, plus Postgres, registry, Traefik |
| Session services address | fixed ports (8080, 8082, 8083...) | `https://<public host>/sessions/session-<id>/<service>`, given to Argus when joining |

## Deploy a local cluster

### Prerequisites

- mise (it installs the `nomad` CLI used below, see `mise.toml`).
- Docker: Linux, or Docker Desktop on macOS. With OrbStack installed, macOS uses OrbStack VMs instead (see Settings).
  - On macOS on Apple silicon, the amd64 images (orchestrator, session manager) need Rosetta:
    `softwareupdate --install-rosetta --agree-to-license`, then restart Docker Desktop.
  - Memory: a session reserves about 9 GB and the infrastructure about 2.5 GB: give Docker Desktop at least 12 GB.
- The Twin-CR images, built with compose (`./setup.sh`, or `docker compose build`): they are pushed from there to the
  registry of the cluster.
- `simulators.zip` in the Twin-CR root (the archive the session manager image is built from): it is extracted on every
  node for the sessions.

### Deploy

From Twin-CR (or from a repository including Twin-CR as a submodule: `mise -C Twin-CR run infra`):

```bash
mise run infra
```

It:
1. creates the cluster: a privileged container `twincr_target` (network `twincr_net`, node address 172.28.0.2) running
   Nomad, Consul and Vault, then Traefik, Postgres, a Docker registry, Garage and Keycloak as Nomad jobs
   (`infra/site.yml`);
2. pushes the Twin-CR images to its registry (`mise run infra:push`, also usable alone after a rebuild);
3. deploys the session manager (`infra/apps.yml`, `make -C infra apps`), once its image is in the registry.

A run takes several minutes and can be repeated: it only changes what differs. Rebuilt images are used by the next
sessions (pulled again at each session start).

Stop the cluster with `mise run infra:stop` and restart it with `mise run infra`: its state is kept. Removing the
`twincr_target` container instead loses it (Vault and its certificate authority, Garage data, session manager database).

The infrastructure and the compose stack use the same host ports (443, 8080, 8090): stop one before starting the other.

### Settings

Per machine, in a git-ignored `mise.local.toml` next to `mise.toml` (`[env]` section), all optional:

| Variable | Default | Use |
|---|---|---|
| `TWINCR_INFRA_BACKEND` | `orbstack` on macOS if its CLI is installed, else `docker` | Where the cluster runs |
| `TWINCR_REGISTRY_PORT` | 5000, 5001 on macOS (AirPlay uses 5000) | Host port of the registry |
| `TWINCR_REGISTRY` | `127.0.0.1:<TWINCR_REGISTRY_PORT>` | Registry `infra:push` pushes to |
| `TWINCR_COMPOSE_DIR` | the repository including Twin-CR as a submodule if it has a `docker-compose.yaml`, else Twin-CR | Compose project whose images are pushed |
| `TWINCR_DYNAWO_RULES_DIR` | `dynawo_rules/` of that repository, if any | Extra Dynawo model rules of the session manager |

Ansible variables (`infra/group_vars/all.yml`): `public_url` (`https://localhost`) is the address of the services used
by Argus; set it to the DNS name of the cluster entry point for a remote cluster.

### Remote cluster

Copy `infra/inventories/remote.ini.example` to `infra/inventories/<env>.ini`, set `public_url`, then
`make -C infra deploy ENV=<env>`, push the images to the registry of that cluster, and `make -C infra apps ENV=<env>`.

## Access

### Argus

In the Argus config (`config.json` in its config folder, e.g. on macOS
`~/Library/Application Support/com.twincr.com.twincr.argus/config.json`):
- `keycloak_url`: `https://localhost` (default; the same as with compose)
- `session_manager_url`: `http://localhost:8090` (default) or `https://localhost/lobby`

An existing `config.json` keeps its values: edit it after an upgrade. The login opens Keycloak in the browser.

Predefined users (development only, the password is the user name):

| User | Roles |
|---|---|
| `alice` | creates templates and sessions |
| `bob` | joins sessions as game master |
| `john` | everything, plus the `infra_admin` role (administration of the infrastructure) |

### Services and interfaces

| Service | Address | Notes |
|---|---|---|
| Keycloak | `https://localhost` | Admin console `https://localhost/admin` (master realm admin: Vault `secret/keycloak`) |
| Session manager | `https://localhost/lobby`, `http://localhost:8090` | API docs: `http://localhost:8090/docs` (not behind `/lobby`) |
| Services of a session | `https://localhost/sessions/session-<id>/{argus-scada,argus-gm,twincr-core,configurator-client,clickhouse}` | ClickHouse query page: `.../clickhouse/play`, with `https://localhost/sessions/session-<id>/clickhouse/` in its URL field |
| Nomad UI | `http://localhost:4646/ui` | Token: `docker exec twincr_target cat /etc/nomad.d/nomad.token` |
| Consul UI | `http://localhost:8500/ui` | Health checks of every service, sessions included |
| Vault UI | `http://localhost:8200/ui` | Root token: `/etc/vault.d/vault.creds` in `twincr_target` |
| Traefik dashboard | `http://localhost:8080/dashboard/` | All routes, sessions included |
| Registry | `http://localhost:5001/v2/_catalog` (5000 on Linux) | Images used by the sessions |

The HTTPS certificate is issued by the certificate authority of the cluster (Vault), not trusted by default. To trust it
(optional, browsers otherwise ask to accept it): get it from `http://localhost:8200/v1/pki/ca/pem`, then on macOS
`security add-trusted-cert -r trustRoot -k ~/Library/Keychains/login.keychain-db <file>` (no sudo needed). It changes if
the cluster is recreated.

Interactive API docs behind a path (`.../configurator-client/docs`, the Swagger pages of the Argus backends) do not
load: they request their files at the root. The admin interfaces also have host names (`nomad.twin.local`...), unused
without DNS entries.

## Contexts (templates)

A session starts from a context: a `config.toml` and its input files, stored in Garage (bucket `context-library`,
`CONTEXTS/<context id>/DATA/`). Create it as a template of the session manager:
- from Argus: lobby, new template;
- or through the session manager API, e.g. with a `config.toml` and its files as they are (`.../examples/Nordic`, after
  its `cfg.sh` if it has one):
  `POST /templates/new_template_expert` (multipart: `template_name`, `folder_id`, `config_toml_file`, `files` and their
  `relative_paths`), with a Keycloak token of the `session-manager-client` client (see `http://localhost:8090/docs`).

The context id is the `uuid` of the template.

## Sessions

### From Argus

1. Lobby: create a session from a template, then launch it. The session manager submits the Nomad job `session-<id>`
   and returns once the session is initialized and its services answer (about 20 s, up to a minute when images are
   pulled).
2. Join it with one of its keys (game master, operator, or golden key): Argus connects to the services of the session.
3. Start the simulation from Argus.
4. At the end of the simulation, or if the orchestrator crashes, the simulation is archived (bucket `archive`) and the
   session stays up: its services and logs remain available.
5. Stop it from the lobby: archive if not done yet, then the job is stopped (its logs stay in Nomad until garbage
   collected). Deleting the session removes the job.

### With the Nomad CLI (development)

Sessions started this way are unknown to the session manager.

```bash
export NOMAD_ADDR=http://localhost:4646
export NOMAD_TOKEN=$(docker exec twincr_target cat /etc/nomad.d/nomad.token)

nomad job run -var session_id=session-test -var context_id=<context id> docs/infra/twincr-session.nomad.hcl
# Optional: -var config_path=config.toml -var scenario_id=<DSL file of the context>
curl https://localhost/sessions/session-test/configurator-client/start   # Start the simulation
nomad job stop session-test          # Stop (add -purge to remove the job)
```

### Follow and debug

```bash
nomad job status session-<id>                         # Allocation of the session and its tasks
nomad alloc status <alloc>                            # Task events, ports
nomad alloc logs [-stderr] <alloc> <task>             # twincr-core, configurator-client, argus-scada...
nomad alloc exec -task <task> <alloc> <command>
curl http://localhost:8500/v1/health/checks/session-session-<id>-<service>   # Health of a service
```

The Argus backends of a session have no fixed port: `nomad alloc status <alloc>` shows them (on 172.28.0.2, not
reachable from macOS, where a relay container on the `twincr_net` network can publish one).

## Troubleshooting

- `exec /bin/sh: exec format error` when building or running amd64 images on macOS: Rosetta is missing (see
  prerequisites).
- A session does not start: `nomad job status session-<id>`, then the events and logs of its failed task. A session
  needs about 9 GB of free memory in the cluster.
- After `mise run infra`, the session manager is unreachable for a few seconds while its health check passes.
