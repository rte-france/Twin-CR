/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

export type User = {
  username: string;
  game_session_id: number | null;
  role: string[];
};

export type GameSessionPublic = {
  name: string;
  state: State;
  id: number;
  started_at: string | null;
  ended_at: string | null;
  participants: User[];
  author: string;
};

export type GameSessionCreate = {
  name: string;
  dsl_name: string;
  config_toml_name: string;
  templateId: number;
};

export type NewFolder = {
  name: string;
  parent_id: number;
};

export type TemplateFolder = {
  node_id: number;
  path: string;
};

export type TemplateFile = {
  /** config.toml key when the file is declared there, else "jobs_dependency" | "other" | "generated" */
  role: string;
  /** path relative to the template root */
  filename: string;
  s3_key: string;
};

export type TemplateDetails = {
  name: string;
  uuid: string;
  owner: string;
  files: TemplateFile[];
};

export type TemplateRenamedResponse = {
  template_id: number;
  template_name: string;
};

export type State = "warmup" | "ready" | "ongoing" | "cleanup" | "ended";

export const SessionState = {
  // Warmup and Cleanup are not produced by the backend yet; they are for when
  // the infra brings each session's stack up and down.
  Warmup: "warmup",
  Ready: "ready",
  Ongoing: "ongoing",
  Cleanup: "cleanup",
  Ended: "ended",
} as const;

export type SessionState = typeof SessionState[keyof typeof SessionState];

export type GameSession = {
  id: number;
  name: string;
  state: State;
  started_at: string | null;
  ended_at: string | null;
  password_gm: string | null;
  password_operator: string | null;
  author: string | null;
  scada_backend_url: string | null;
  gm_backend_url: string | null;
  dsl_backend_url: string | null;
  template_name: string | null;
};

export type AccessKeyTyped = {
  type: string;
  id: number;
  password: string;
  validity_limit: string; // ISO datetime
  usage: "unique" | "multi";
  revoked: boolean;
};

export type FileInfo = {
  size: number;
};
