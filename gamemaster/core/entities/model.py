"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Pydantic models used by the game master feature.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class ActionDetails(BaseModel):
    """Payload describing how a simulator element should be altered."""

    elementId: Optional[Union[str, List[str]]] = None
    percentage: Optional[float] = None
    component_type: Optional[str] = None
    id: Optional[str] = None
    message: Optional[str] = None
    additional_params: Optional[Dict[str, Any]] = None
    links: Optional[List[Dict[str, str]]] = None
    nodes: Optional[List[str]] = None
    delay_function: Optional[Dict[str, Any]] = None
    drop_function: Optional[Dict[str, Any]] = None
    corruption_functions: Optional[List[Dict[str, Any]]] = None

    class Config:
        exclude_none = True


class Action(BaseModel):
    """Single scheduled action for the simulator timeline."""

    timestamp: float
    actionType: str
    details: ActionDetails
    interval_start: Optional[float] = None
    interval_end: Optional[float] = None
    law: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        exclude_none = True


class SimulationConfig(BaseModel):
    """Full simulator configuration derived from DSL or control payloads."""

    simulationName: str
    startTime: float
    endTime: float
    timeStep: float
    currentStep: float
    actions: List[Action]

    @validator("endTime")
    def _end_time_after_start(cls, end_time, values):
        """Ensure the simulation duration is positive."""
        start = values.get("startTime")
        if start is not None and end_time <= start:
            raise ValueError("endTime must be greater than startTime")
        return end_time

    @validator("timeStep")
    def _time_step_positive(cls, time_step):
        """Ensure the simulation time step is strictly positive."""
        if time_step <= 0:
            raise ValueError("timeStep must be greater than 0")
        return time_step

    @validator("currentStep")
    def _current_step_within_bounds(cls, current_step, values):
        """Ensure `currentStep` falls between `startTime` and `endTime`."""
        start = values.get("startTime")
        end = values.get("endTime")
        if start is not None and current_step < start:
            raise ValueError("currentStep must be greater than or equal to startTime")
        if end is not None and current_step > end:
            raise ValueError("currentStep must be less than or equal to endTime")
        return current_step

    class Config:
        exclude_none = True


class AggregateInput(BaseModel):
    """Payload used by the simulator control endpoint to advance time."""

    current_time: float = Field(
        ...,
        description="Absolute simulation time in seconds (relative to simulation start)",
    )


class AggregateOutput(SimulationConfig):
    """Alias for the response used by simulator control endpoints."""


class ControlInput(BaseModel):
    """Direct control command issued for a single simulator element."""

    control_type: str = Field(
        ...,
        description="e.g. 'switch', 'load', 'generator', 'fault'",
    )
    action: str = Field(
        ...,
        description="e.g. 'open', 'close', 'increase', 'decrease', 'apply', 'clear'",
    )
    id: str = Field(..., description="Unique identifier of the element")
    value: Optional[float] = Field(
        None, description="Value for 'increase'/'decrease' actions"
    )
    timestamp: float = Field(
        ...,
        description="Timestamp in seconds (relative to simulation start) when the action should occur",
    )
    interval_start: Optional[float] = None
    interval_end: Optional[float] = None
    law: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ClusterControlInput(BaseModel):
    """Cluster-level control command that targets multiple simulator elements."""

    control_type: str = Field(
        ...,
        description="e.g. 'switch', 'load', 'generator', 'fault'",
    )
    action: str = Field(
        ...,
        description="e.g. 'open', 'close', 'increase', 'decrease', 'apply', 'clear'",
    )
    target: Union[List[str], Dict[str, Any]] = Field(
        ...,
        description="List of component IDs (static) or dynamic cluster specification (dict)",
    )
    timestamp: float = Field(
        ...,
        description="Timestamp in seconds (relative to simulation start) when the action should occur",
    )
    value: Optional[float] = Field(
        None, description="Value for 'increase'/'decrease' actions"
    )
    interval_start: Optional[float] = None
    interval_end: Optional[float] = None
    law: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
