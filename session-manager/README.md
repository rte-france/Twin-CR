# Session Manager

## Purpose
This micro-service is a backend to handle session CRUDs, and argus client authorization.

### Installation for dev

We describe here the installation process where the other services run with docker and the session-manager is launched manually.

1. Install using UV:
    ```bash
    uv sync
    ```
2. Copy the env-example file in a .env file in the session-manager folder. 
   - Uncomment the following variables and complete SIMULATORS_PATH and EXTRA_RULES_PATH.  
     ```
     # Native runs only (uv, other services in docker): uncomment and adapt.
     # Defaults are the in-container paths used by docker.
     #KEYCLOAK_VERIFY_TLS=false  # [native] Keycloak's host port serves a self-signed cert
     #KEYCLOAK_INTERNAL_URL=https://localhost:8443  # [native] default http://keycloak:8080
     #SIMULATORS_PATH=/home/session-manager/simulators  # [native]
     #EXTRA_RULES_PATH=/home/session-manager/dynawo_rules  # [native]
     ```
   - Set the hosts to "localhost" 
     ```
     GARAGE_HOST=localhost
     CONFIGURATOR_HOST=localhost
     ```
3. Then to run the server :
    ```bash
    uv run uvicorn backend.main:app --host 0.0.0.0 --port 8090
    ```
The tables are created on startup, along with the Root/Users/Common folders of the
template tree. `DB_URL` decides where the database lives; unset, it is
`database.db` in the working directory, so deleting that file resets everything.

### Installation with Docker

1. Copy the env-example file in a .env file in the session-manager folder, and complete it.
2. Use the compose file "docker-compose-session-manager.yaml":
    ```bash
    docker compose -f docker-compose-session-manager.yaml up -d
    ```

Here the compose file sets `DB_URL` to `sqlite:////data/database.db` and mounts the
`session-manager-db` volume there, so templates and sessions survive a rebuild or a
`docker compose down`. To reset the database, either remove the volume:
```bash
docker compose -f docker-compose-session-manager.yaml down -v
```
or delete the file and restart, which re-creates the tables and re-seeds the tree:
```bash
docker exec session_manager rm /data/database.db
docker compose -f docker-compose-session-manager.yaml restart session-manager
```

Note that the uploaded template files live in the garage bucket, not in the
database, so resetting one without the other leaves objects that nothing
references.

### Troubleshooting

Set `DB_ECHO=1` to log every SQL statement. It is off by default because the
output includes bound parameters, which for access keys means their passwords in
clear, and because it accounts for the large majority of the log volume.
