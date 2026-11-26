"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import logging

import boto3

from src.export_clickhouse_tables import Clickhouse_Tables
from src.config import BUCKET, S3_ENDPOINT, S3_ACCESS_KEY, S3_PRIVATE_KEY, BUCKET_ARCHIVE
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
        failed = []
        for table in Clickhouse_Tables:
            query = self.generate_sql_template(context_id, simulation_id, table.name)
            try:
                response = clickhouse_client.raw_query(query=query)
                self.logger.info(f"Archived {table.name} in S3")
            except Exception as e:
                self.logger.error(f"Failed to execute query: {query, e}")
                failed.append(f"{table.name} ({e})")
        if failed:
            raise RuntimeError(f"Archive of {simulation_id} failed for {len(failed)} table(s): {'; '.join(failed)}")

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

    def get_context_prefix(self, context_id):
        return f"CONTEXTS/{context_id}/DATA/"
