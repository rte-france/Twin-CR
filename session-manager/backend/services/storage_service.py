"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

import json
from pathlib import Path
from typing import Optional, List

from botocore.exceptions import ClientError, BotoCoreError
from fastapi import HTTPException

from backend.config import CONTEXT_BUCKET, ARCHIVE_BUCKET
from backend.db.s3_models import Scope, DynawoMetadata
from backend.s3_client import make_s3_client, SIMULATOR_KEY_PREFIX
from backend.simulator.simulator_cache_handler import METADATA_KEY_RE

# A template's files live under DATA/, and the roles manifest sits beside it so
# it never shows up in a listing of the files themselves.
ROLES_OBJECT = "roles.json"


def template_prefix(template_uuid: str) -> str:
    return f"CONTEXTS/{template_uuid}"


def template_data_prefix(template_uuid: str) -> str:
    return f"{template_prefix(template_uuid)}/DATA"


def roles_key(template_uuid: str) -> str:
    return f"{template_prefix(template_uuid)}/{ROLES_OBJECT}"


class StorageService:
    def __init__(self):
        self.s3 = make_s3_client()
        self.context_bucket = CONTEXT_BUCKET

    def upload_file(self, key: str, file_path: str | Path, content_type: str = "application/octet-stream"):
        with open(Path(file_path), "rb") as body:
            self.s3.put_object(
                Bucket=self.context_bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
            )

    def download_file(self, key: str) -> bytes:
        response = self.s3.get_object(
            Bucket=self.context_bucket,
            Key=key,
        )
        return response["Body"].read()

    def get_file_size(self, key: str) -> int:
        response = self.s3.head_object(
            Bucket=self.context_bucket,
            Key=key,
        )
        return response["ContentLength"]

    def delete_file(self, key: str) -> None:
        self.s3.delete_object(
            Bucket=self.context_bucket,
            Key=key,
        )

    def keys_under(self, prefix: str) -> list[str]:
        """Every key under a prefix, following the listing's pagination."""
        keys: list[str] = []
        token: str | None = None
        while True:
            kwargs = {"Bucket": self.context_bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = self.s3.list_objects_v2(**kwargs)
            keys.extend(obj["Key"] for obj in response.get("Contents", []))
            if not response.get("IsTruncated"):
                return keys
            token = response.get("NextContinuationToken")

    def list_template_files(self, template_uuid: str) -> list[str]:
        """
        Paths of a template's files, relative to its DATA prefix.

        The bucket is the authority on which files a template has; nothing
        mirrors this list, so it cannot disagree with itself.
        """
        prefix = f"{template_data_prefix(template_uuid)}/"
        return sorted(key[len(prefix):] for key in self.keys_under(prefix))

    def write_roles(self, template_uuid: str, roles: dict[str, str]) -> None:
        self.s3.put_object(
            Bucket=self.context_bucket,
            Key=roles_key(template_uuid),
            Body=json.dumps(roles, indent=2, sort_keys=True).encode(),
            ContentType="application/json",
        )

    def read_roles(self, template_uuid: str) -> dict[str, str]:
        """
        The role of each file, by relative path.

        Advisory rather than authoritative: a file the manifest does not mention
        still exists, it just has no declared role. A missing or unreadable
        manifest therefore degrades to "no roles known" instead of failing.
        """
        try:
            raw = self.download_file(roles_key(template_uuid))
        except ClientError:
            return {}
        try:
            roles = json.loads(raw)
        except ValueError:
            return {}
        return roles if isinstance(roles, dict) else {}

    def delete_template(self, template_uuid: str) -> None:
        """Everything stored for a template, the roles manifest included."""
        for key in self.keys_under(f"{template_prefix(template_uuid)}/"):
            self.s3.delete_object(Bucket=self.context_bucket, Key=key)

    def list_templates(self, username: str) -> list[str]:
        prefix = f"{username}/"

        response = self.s3.list_objects_v2(
            Bucket=self.context_bucket,
            Prefix=prefix,
            Delimiter="/",
        )

        templates: list[str] = []

        for p in response.get("CommonPrefixes", []):
            full_prefix = p["Prefix"]

            # get only the name
            name = full_prefix.replace(prefix, "").strip("/")

            if name:
                templates.append(name)

        return templates

    def list_dynawo_version(self,
                            scope: Optional[Scope],
                            version: Optional[str],
                            tag: Optional[str]
                            ):
        if version and not version.startswith("v"):
            version = f"v{version}"

        prefix = f"{SIMULATOR_KEY_PREFIX}/{scope.value}/" if scope else f"{SIMULATOR_KEY_PREFIX}/"

        items: List[DynawoMetadata] = []
        try:
            paginator = self.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=ARCHIVE_BUCKET, Prefix=prefix):
                for obj in page.get("Contents", []):
                    entry = _parse_object(obj)
                    if entry is None:
                        continue
                    if version and entry.version != version:
                        continue
                    if tag is not None and entry.tag != tag:
                        continue
                    items.append(entry)
        except (ClientError, BotoCoreError) as e:
            raise HTTPException(status_code=502, detail=f"S3 error: {e}") from e
        return items


def _parse_object(obj: dict) -> Optional[DynawoMetadata]:
    """Build an entry from a list_objects_v2 item, or None if the key
    doesn't follow the expected layout."""
    m = METADATA_KEY_RE.fullmatch(obj["Key"])
    if not m:
        return None
    scope, major, minor, patch, tag = m.groups()
    version = f"v{major}.{minor}.{patch}"
    release = (f"dynawo{'RTE' if scope == 'RTE' else ''}{version}"
               + (f"-{tag}" if tag else ""))
    return DynawoMetadata(
        scope=Scope(scope),
        version=version,
        tag=tag,
        release=release,
        key=obj["Key"],
        size=obj["Size"],
        last_modified=obj["LastModified"],
    )
