# Configurator Client

## About

This sub repo is for the Fast API based server that handles all file transactions with S3 within a game session.
It will load context&scenario files from the S3 storage to the clickhouse instance at startup.
It will load kpi files from clickhouse to the S3 storage at game end.

## How to use

Before this, please make sure you have a working instance to connect to S3.
You can use the one specified in the configurator_server.

### Dev
Dependency on configurator_server and it's credentials, please read first the README of that sub-repo to generate S3 credentials that are used later in this README.

If you instead want to use the file system, set the env variable STORAGE_TYPE=filesystem

1. Install uv
2. In /configurator_client, to create the venv and install dependencies, run
~~~
uv sync
~~~
3. Setup your .env

Create a .env file in /configurator_client by copy pasting the content of the .env-example.

Fill in the S3 credentials that are in the credentials.txt of the configurator_server folder once you have done the initialisation.
- AWS_ACCESS_KEY_ID = Key ID
- AWS_SECRET_ACCESS_KEY = Secret Key

4. (optional) You may upload your context info in S3 using the util script :
~~~
uv run upload_context /path/to/your/config.toml context_id
~~~
e.g.
```bash
uv run upload_context ../docs/orchestrator/examples/Nordic/config.toml Nordic

uv run upload_context ../docs/orchestrator/examples/4Bus/config.toml 4Bus
uv run upload_context ../docs/orchestrator/examples/4Bus_PSCC/config.toml 4Bus_PSCC
````

5. Run the server with
~~~
uv run fastapi dev src/main.py
~~~
