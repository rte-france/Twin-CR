# Configurator Server
## About

This sub repo handles the configurator server, which is a garage based S3 compatible storage solution for context & scenario files.

In this repo you can find :

- docker-compose-garage.yaml

This docker compose runs a Garage and Garage web ui image

- docker-compose-garage-cleanup.yaml

A simple docker utility to wipe the stored objects. Note that it clears the
bind-mounted `garage-data/` directory rather than a docker volume, and that the
session-manager's database is separate: emptying one without the other leaves
either objects nothing references or rows pointing at objects that are gone.

- garage-dev.toml

A default dev configuration for the garage deployment. It holds no secret: the RPC secret,
the admin token and the metrics token come from the `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN`
and `GARAGE_METRICS_TOKEN` environment variables, set in the root `.env` (see `.env-example`).

- init_garage.sh

A script to initialize all one-time administrative tasks of garage, including creating of a key and a bucket.

## Running

1. fill `GARAGE_RPC_SECRET`, `GARAGE_ADMIN_TOKEN` and `GARAGE_METRICS_TOKEN` in the root `.env`
   (`./setup.sh --only secrets` from the root, or the commands given in `.env-example`), then run the docker container

~~~
docker compose --env-file ../.env -f docker-compose-garage.yaml up
~~~

2. run the initialisation script (only do it once)

~~~
./init_garage.sh
~~~

3. access the web UI at http://localhost:3909/
4. access the S3 API at localhost:3900
5. get your access key information in the file created by the init script : credentials.txt


## S3 formatting

We all use one bucket : context-library

The bucket will be indexed by the following path :
~~~
/CONTEXTS
    /${context-id}
        /DATA
            {context-id}.iidm
            game_master_inputs.json
            game_master_outputs.json
            scada_outputs.json
            RTConnectors.dyd
            {context-id}.dyd
            scada_inputs.json
            curves.xml
            {context-id}.jobs
            {context-id}.par
            {context-id}.crv
            cyber_config.json
            asset_simulator_config.json
            geo_data.json
            config.toml
        /SCENARIOS
            ${scenario-id}.dsl
            ...
/RUNS
    /${context-id}
        /${scenario-id}
            ...
~~~
