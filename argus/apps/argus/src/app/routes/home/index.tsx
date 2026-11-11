/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Shell } from "@/app/layout/shell";

export const Home = (props: { windowLabel: string; themeSyncId: string }) => {
  return (
    <Shell windowLabel={props.windowLabel} themeSyncId={props.themeSyncId} />
  );
};
