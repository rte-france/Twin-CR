# Keycloak service

## Getting Started

Create a `.env` file following the `.env-example` one.

In keycloak folder, launch keycloak service with
```bash
docker compose -f docker-compose.yaml up
```

The service runs at `http://localhost:8443`

## Description
This version uses two files:
   - Dockerfile to create the custom image
   - docker-compose.yaml to launch the service

It uses `imports_keycloak/realm-export.json` to create a specific configuration:
a "twincr" realm with a client "session-manager-client" and some roles
("template_manager", "session_launcher", "participant_gm" and
"participant_operator").

Two demo users are created via seed.sh (see keycloak-seed folder): alice and
bob. Their password are their username. alice has `template_manager` and
`session_launcher`; bob has `participant_gm`.

Note that `--import-realm` only imports when the realm does not already exist,
and `start-dev` keeps its database inside the container. So after editing the
realm export the container has to be replaced, not restarted — a restart keeps
the old realm and silently ignores your edit. From the repository root, so it
targets the running stack rather than starting a second one:

```bash
docker compose up -d --force-recreate keycloak keycloak-seed
```

`keycloak-seed` is included because a re-imported realm has no users.

Keycloak uses https with certificates embedded in docker container.

## Development-only settings

- The certificate is self-signed and its key is unencrypted.
