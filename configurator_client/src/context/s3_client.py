"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import logging
import tempfile
from pathlib import Path

import boto3
import toml

from src.export_clickhouse_tables import Clickhouse_Tables
from src.game_master_client import GameMasterClient
from src.config import BUCKET, DSL_SERVER_URL, S3_ENDPOINT, S3_ACCESS_KEY, S3_PRIVATE_KEY, BUCKET_ARCHIVE
from src.context.context_client import Context_Client


class S3_Client(Context_Client):
    def __init__(self):
        self.logger = self.init_logger()
        self.s3 = boto3.client("s3", region_name="garage")
        self.logger.info("Checking buckets availability")
        bucket_found = False
        all_buckets = self.s3.list_buckets()
        for bucket in all_buckets["Buckets"]:
            if bucket["Name"] == BUCKET:
                bucket_found = True
            self.logger.info(bucket["Name"])
        if not bucket_found:
            raise Exception("Bucket not found")
        else:
            self.logger.info("Bucket found")

    def init_logger(self):
        logger: logging.Logger = logging.getLogger("configurator.client")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def generate_sql_template(self, context_id, simulation_id, table_name):
        return f"""
            INSERT INTO FUNCTION s3(
                '{S3_ENDPOINT}/{BUCKET_ARCHIVE}/{context_id}/{simulation_id}/{table_name}.csv.gz',
                '{S3_ACCESS_KEY}',
                '{S3_PRIVATE_KEY}',
                'CSVWithNames',
                compression='gzip/gz'
            ) SELECT * FROM "{simulation_id}"."{table_name}" """

    def archive(self, clickhouse_client, context_id, simulation_id):
        # Contact click house and export all tables in export_clickhouse_tables in a dump
        for table in Clickhouse_Tables:
            query = self.generate_sql_template(context_id, simulation_id, table.name)
            try:
                response = clickhouse_client.raw_query(query=query)
                self.logger.info(f"Archived {table.name} in S3")
            except Exception as e:
                self.logger.error(f"Failed to execute query: {query, e}")

    def init_context_and_scenario_files(self, clickhouse_client, context_id, scenario_id, simulation_id, config_path):
        paginator = self.s3.get_paginator("list_objects_v2")
        prefix = self.get_context_prefix(context_id)
        pages = paginator.paginate(Bucket=BUCKET, Prefix=prefix)
        for page in pages:
            for obj in page["Contents"]:
                key = obj["Key"]
                if key.endswith("/"):
                    continue
                data = self.s3.get_object(Bucket=BUCKET, Key=key)
                relative_key = key.removeprefix(prefix)
                self.logger.info(f"Uploading {relative_key}")
                try:
                    contents = data["Body"].read()
                    clickhouse_client.insert(
                        f"{simulation_id}.InputFiles",
                        [(relative_key, contents)],
                        column_names=["input_file", "content"]
                    )
                except Exception as e:
                    self.logger.error(e)

    def init_game_master(self, config_path, context_id, scenario_id, simulation_id):
        paginator = self.s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=BUCKET, Prefix=self.get_context_prefix(context_id))
        iidm_key = None
        dsl_key = None
        for page in pages:
            for obj in page["Contents"]:
                key = obj["Key"]
                if self.is_iidm(key):
                    iidm_key = key
                    self.logger.info(f"found iidm key {key}")
                if scenario_id and key.endswith(scenario_id):
                    dsl_key = key
                    self.logger.info(f"found dsl key {key}")
        config_key = self.get_context_prefix(context_id) + config_path
        self.upload_game_master_files(config_key, iidm_key, dsl_key, simulation_id)

    def upload_game_master_files(self, config_key, iidm_key, dsl_key, simulation_id):
        game_master_client = GameMasterClient(DSL_SERVER_URL)
        game_master_artifact = "Nordic"

        with tempfile.NamedTemporaryFile(suffix=".iidm", delete_on_close=False) as tmp:
            self.s3.download_file(BUCKET, iidm_key, tmp.name)
            self.logger.info(f"Uploading {iidm_key} to game master")
            reply = game_master_client.upload_iidm(Path(tmp.name), game_master_artifact)
            # Use the artifact_id from server if provided; otherwise keep the current one
            game_master_artifact = reply.get("artifact_id", game_master_artifact)
            self.logger.info("IIDM upload received the following reply\n", reply)
        if dsl_key is not None:
            with tempfile.NamedTemporaryFile(suffix=".dsl", delete_on_close=False) as tmp:
                self.s3.download_file(BUCKET, dsl_key, tmp.name)
                tmp.close()
                self.logger.info(f"Uploading DSL file {dsl_key}")
                reply = game_master_client.init_simulation(Path(tmp.name), simulation_id, game_master_artifact)
        else:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=True) as tmp_config:
                self.s3.download_file(BUCKET, config_key, tmp_config.name)
                config = toml.load(tmp_config.name)
            # Create a temporary empty dsl file and send it
            with tempfile.NamedTemporaryFile(mode="w", suffix=".dsl", delete=True) as tmp:
                empty_dsl_path = tmp.name
                with open(empty_dsl_path, 'w') as f:
                    f.write(
                        "set simulation duration to 999999999 seconds;\n"
                        f"set time step to {config['master']['period']} seconds;\n"
                    )
                self.logger.info("Uploading empty DSL file")
                reply = game_master_client.init_simulation(Path(empty_dsl_path), simulation_id, game_master_artifact)
        self.logger.info("DSL upload received the following reply\n", reply)

    def is_iidm(self, key):
        return key.endswith(".iidm") or key.endswith(".xiidm")

    def get_context_prefix(self, context_id):
        return f"CONTEXTS/{context_id}/DATA/"
