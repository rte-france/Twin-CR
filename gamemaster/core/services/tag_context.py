"""
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.

Helpers for seeding DSL interpreters with simulation-scoped tag bindings.
"""

from __future__ import annotations

from typing import Dict, Mapping, Optional


def seed_labels(
    interpreter,
    event_store,
    simulation: Optional[str],
    *,
    base_labels: Optional[Mapping[str, str]] = None,
    exclude_event_id: Optional[str] = None,
) -> Dict[str, str]:
    """Populate ``interpreter.labels`` with the latest known tag bindings."""
    labels: Dict[str, str] = {}
    persisted: Dict[str, str] = {}
    store_lookup_ok = False

    if simulation and event_store is not None:
        try:
            persisted = event_store.get_latest_tag_bindings(
                simulation,
                exclude_event_id=exclude_event_id,
            )
            store_lookup_ok = True
        except Exception:
            persisted = {}

    if not store_lookup_ok and base_labels:
        for tag, event_id in base_labels.items():
            if not tag or not event_id:
                continue
            if exclude_event_id and str(event_id) == str(exclude_event_id):
                continue
            labels[str(tag)] = str(event_id)

    if persisted:
        labels.update({str(tag): str(event_id) for tag, event_id in persisted.items()})

    interpreter.labels = labels
    return labels


__all__ = ["seed_labels"]
