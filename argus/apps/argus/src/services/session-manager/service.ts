/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { getValidToken } from "@/features/auth";
import { getArgusConfig } from "@/services/config";
import {
  AccessKeyTyped,
  GameSession,
  GameSessionCreate,
  NewFolder,
  TemplateDetails,
  TemplateFolder,
  FileInfo,
} from "./types";
import type { TreeNode } from "@/features/lobby/types";

/** A rejection's message, whatever was thrown. */
function describe(err: unknown): string {
  if (err instanceof Error) return err.message;
  return err === undefined ? "no reason given" : String(err);
}

/** apiFetch without the JSON decoding, for endpoints that return raw bytes. */
export async function apiFetchRaw(url: string, options: RequestInit = {}): Promise<Response> {
  // Refresh failures are reported to the auth store by getValidToken itself.
  const token = await getValidToken();

  const isFormData = options.body instanceof FormData;
  const isJsonObject =
    options.body && typeof options.body === "object" && !isFormData;

  // Without this wrapper a network failure only reads "Load failed", with no
  // hint of which server it came from.
  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      body: isJsonObject ? JSON.stringify(options.body) : options.body,
      headers: {
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
      },
    });
  } catch (err) {
    throw new Error(`No response from ${new URL(url).origin}: ${describe(err)}`);
  }

  if (!response.ok) {
    let message = `API error: ${response.status}`;
    try {
      const rawText = await response.text();
      message = `API error: ${response.status} - ${rawText}`;
      const body = JSON.parse(rawText);
      if (body?.detail) {
        message =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      // no JSON body or read failed, keep message
    }
    throw new Error(message);
  }

  return response;
}

export async function apiFetch(url: string, options: RequestInit = {}) {
  return (await apiFetchRaw(url, options)).json();
}

// SESSIONS

export async function getSessions(): Promise<GameSession[]> {
  return apiFetch(getArgusConfig().session_manager_url + "/sessions", {
    method: "GET",
  });
}

export async function getMySessions(): Promise<GameSession[]> {
  return apiFetch(getArgusConfig().session_manager_url + "/sessions/me", {
    method: "GET",
  });
}

export async function createSession(sessionData: GameSessionCreate) {
  return apiFetch(
    getArgusConfig().session_manager_url + "/sessions/new_session",
    {
      method: "POST",
      body: JSON.stringify(sessionData),
    },
  );
}

export async function getAccessKeys(
  sessionId: number,
): Promise<AccessKeyTyped[]> {
  return apiFetch(
    `${getArgusConfig().session_manager_url}/sessions/keys/${sessionId}`,
    {
      method: "GET",
    },
  );
}

export async function setAccessKeys(accessKeyData: AccessKeyTyped) {
  return apiFetch(getArgusConfig().session_manager_url + "/sessions/key", {
    method: "POST",
    body: JSON.stringify(accessKeyData),
  });
}

export async function launchSession(sessionId: number) {
  return apiFetch(
    `${getArgusConfig().session_manager_url}/sessions/${sessionId}/launch`,
    {
      method: "POST",
    },
  );
}

export async function stopSession(sessionId: number) {
  return apiFetch(
    `${getArgusConfig().session_manager_url}/sessions/${sessionId}/stop`,
    {
      method: "POST",
    },
  );
}

export async function deleteSession(sessionId: number) {
  return apiFetch(
    `${getArgusConfig().session_manager_url}/sessions/${sessionId}/delete`,
    {
      method: "DELETE",
    },
  );
}

export async function connectSession(params: {
  game_session_id: number;
  password_gm: string;
  password_operator: string;
}) {
  return apiFetch(`${getArgusConfig().session_manager_url}/sessions/connect`, {
    method: "POST",
    body: JSON.stringify(params), // Credentials in body, not query string that is logged
  });
}

// TREE VIEW

export async function getFolderChildren(folderId: number): Promise<TreeNode[]> {
  return apiFetch(
    `${getArgusConfig().session_manager_url}/tree/${folderId}/children`,
    {
      method: "GET",
    },
  );
}

export async function getTree(folderId: number): Promise<TreeNode[]> {
  return apiFetch(`${getArgusConfig().session_manager_url}/tree/${folderId}/subtree`, {
    method: "GET",
  });
}

export async function getTemplateFolders(): Promise<TemplateFolder[]> {
  return apiFetch(`${getArgusConfig().session_manager_url}/tree/folders`, {
    method: "GET",
  });
}

export async function initUserTree(): Promise<TreeNode[]> {
  return apiFetch(`${getArgusConfig().session_manager_url}/tree/init_user`, {
    method: "GET",
  });
}

export async function newFolder(newFolder: NewFolder) {
  return apiFetch(getArgusConfig().session_manager_url + "/tree/new_folder", {
    method: "POST",
    body: JSON.stringify(newFolder),
  });
}

export async function deleteNode(
  nodeId: number,
): Promise<{ parent_id: number | null }> {
  return apiFetch(getArgusConfig().session_manager_url + `/tree/${nodeId}`, {
    method: "DELETE",
  });
}

// TEMPLATES

export async function getTemplateDetails(
  template_id: number,
): Promise<TemplateDetails> {
  return apiFetch(
    `${getArgusConfig().session_manager_url}/templates/${template_id}`,
    {
      method: "GET",
    },
  );
}

export async function createTemplate(
  templateName: string,
  folderId: number,
  jobFile: File,
  dynawoFiles: { relativePath: string; file: File }[],
  optionalFiles: Record<string, File>,
  period: number,
  dynawoVariant: "public" | "rte",
  otherFiles: File[] = [],
  automataCommands: string[] = [],
) {
  const formData = new FormData();
  formData.append("template_name", templateName);
  formData.append("folder_id", folderId.toString());
  formData.append("job_file", jobFile);
  formData.append("period", String(period));
  formData.append("dynawo_variant", dynawoVariant);

  for (const { relativePath, file } of dynawoFiles) {
    formData.append("dynawo_files", file);
    formData.append("dynawo_relative_paths", relativePath);
  }
  for (const [field, file] of Object.entries(optionalFiles)) {
    if (file) {
      formData.append(field, file);
    }
  }
  for (const file of otherFiles) {
    formData.append("other_files", file);
  }
  for (const command of automataCommands) {
    formData.append("automata_commands", command);
  }

  return apiFetch(
    getArgusConfig().session_manager_url + "/templates/new_template",
    {
      method: "POST",
      body: formData,
    },
  );
}

/**
 * Names a Dynawo jobs or dyd file references. The convention lives server-side
 * so it is not reimplemented here; callers walk the graph by calling this for
 * each dyd they discover.
 */
export async function dynawoDependencies(file: File): Promise<string[]> {
  const formData = new FormData();
  formData.append("xml_file", file);
  const result = await apiFetch(
    getArgusConfig().session_manager_url + "/templates/dynawo_dependencies",
    { method: "POST", body: formData },
  );
  return result.references;
}

/** Upload an already-valid context: the config.toml is taken as authoritative. */
export async function createTemplateExpert(
  templateName: string,
  folderId: number,
  configFile: File,
  files: { relativePath: string; file: File }[],
) {
  const formData = new FormData();
  formData.append("template_name", templateName);
  formData.append("folder_id", folderId.toString());
  formData.append("config_toml_file", configFile);

  for (const { relativePath, file } of files) {
    formData.append("files", file);
    formData.append("relative_paths", relativePath);
  }

  return apiFetch(
    getArgusConfig().session_manager_url + "/templates/new_template_expert",
    {
      method: "POST",
      body: formData,
    },
  );
}

export async function renameTemplate(
  templateId: number,
  templateNewName: string
) {
  const params = new URLSearchParams({
    template_new_name: templateNewName,
  });

  return apiFetch(
    `${getArgusConfig().session_manager_url}/templates/rename/${templateId}?${params}`, {
      method: "PATCH",
    }
  );
}

//STORAGE

/**
 * An S3 key as a URL path.
 *
 * Encoded per segment, keeping the slashes: a key is a path. Interpolating it
 * raw truncates at a `#` (the rest becomes a fragment and is never sent) and
 * turns anything after a `?` into a query string, both silently.
 */
function keyAsPath(key: string) {
  return key.split("/").map(encodeURIComponent).join("/");
}

/** A stored file's raw bytes; call .text() or .bytes() on the result as fits. */
export async function getFileContent(key: string): Promise<Response> {
  return apiFetchRaw(
    `${getArgusConfig().session_manager_url}/file/${keyAsPath(key)}`,
    {
      method: "GET",
    },
  );
}

export async function getFileInfo(storageKey: string): Promise<FileInfo> {
  return apiFetch(
    `${getArgusConfig().session_manager_url}/file-info/${keyAsPath(storageKey)}`,
    {
      method: "GET",
    },
  );
}

/**
 * Read a timestamp from the session-manager as UTC.
 *
 * The columns are declared timezone-aware, but SQLite has no timezone type, so
 * the offset is lost on the way out and the API serialises a bare
 * `2026-09-07T08:00:10.592029`. `new Date` reads that as local time, which
 * shifts every displayed time by the viewer's offset, so the zone has to be put
 * back. Still needed after the move to Postgres? No — drop this then.
 */
export function parseUtcDate(dateStr: string): Date {
  return new Date(dateStr.replace(" ", "T") + "Z");
}
