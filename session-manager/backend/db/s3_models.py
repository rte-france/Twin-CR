"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Scope(str, Enum):
    public = "public"
    RTE = "RTE"

class DynawoMetadata(BaseModel):
    scope: Scope = Field(description="Distribution: public or RTE")
    version: str = Field(description="Semver version, without tag",
                         examples=["v1.6.0"])
    tag: Optional[str] = Field(default=None, description="Optional tag",
                               examples=["rc1"])
    release: str = Field(
        description="Release name, as accepted by dynawo_cache.get_or_retrieve",
        examples=["dynawoRTEv1.6.0-rc1"])
    key: str = Field(description="S3 key of the metadata archive",
                     examples=["simulators/RTE/v1.6.0-rc1/metadata.zip"])
    size: int = Field(description="Archive size in bytes")
    last_modified: datetime


class DynawoMetadataList(BaseModel):
    count: int
    items: List[DynawoMetadata]