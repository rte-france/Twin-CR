/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

type TreeNodeBase = {
  id: number;
  parent_id: number;
  name: string;
  owner: string;
  has_children: boolean;
  /** Populated lazily as folders are expanded; absent until then. */
  children?: TreeNode[];
};

export type TreeNode =
  | (TreeNodeBase & { type: "folder"; template_id: null })
  | (TreeNodeBase & { type: "template"; template_id: number });
