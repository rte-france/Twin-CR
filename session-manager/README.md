# Session Manager

## Purpose
This micro-service is a backend to handle session CRUDs, and argus client authorization.

### Installation for dev

1. Install using UV:
    ```bash
    uv sync
    ```
2. Copy the env-example file in a .env file in the session-manager folder, and complete it.
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

### Using the simulator archive tool
First install the package :

```bash
uv run pip install -e .
```
Then run :
```bash
uv run tools/upload_dynawo.py path/to/your/dynawo.zip
```

The upload script expects a zip name like : dynawo(RTE)?vX.Y.Z(-(.*))?.zip

You can then force the cache resolution using (or just let it get resolved automatically the first time):

```bash
uv run backend/simulator/simulator_cache_handler.py dynawov1.8.1
```

### Troubleshooting

Set `DB_ECHO=1` to log every SQL statement. It is off by default because the
output includes bound parameters, which for access keys means their passwords in
clear, and because it accounts for the large majority of the log volume.
