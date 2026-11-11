/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Icon } from "@iconify-icon/solid";

interface IconResolverProps {
  name: string;
  size?: number;
  class?: string;
}

export const IconResolver = (props: IconResolverProps) => {
  return (
    <Icon
      icon={props.name || "lucide:help-circle"}
      width={props.size || 18}
      height={props.size || 18}
      class={props.class}
      style={{ display: "inline-block", "vertical-align": "middle" }}
    />
  );
};
