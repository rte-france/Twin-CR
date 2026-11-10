/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { Context, Data, Effect, Layer, Schema } from "effect";
import {
  FetchHttpClient,
  HttpApi,
  HttpApiClient,
  HttpApiEndpoint,
  HttpApiGroup,
  HttpApiSchema,
  HttpClient,
  HttpClientRequest,
  HttpClientResponse,
  Multipart,
} from "@effect/platform";
import { ConfigService } from "@/services/config";
import { kc } from "@/features/auth";

export class LobbyHttpError extends Data.TaggedError("LobbyHttpError")<{
  readonly message: string;
  readonly endpoint: string;
}> {}
export class LobbyDecodeError extends Data.TaggedError("LobbyDecodeError")<{
  readonly message: string;
  readonly endpoint: string;
}> {}
export class LobbyNotFoundError extends Data.TaggedError("LobbyNotFoundError")<{
  readonly id: string;
}> {}
export type LobbyError = LobbyHttpError | LobbyDecodeError | LobbyNotFoundError;

export interface FileNode {
  readonly id: string;
  readonly name: string;
  readonly is_directory: boolean;
  readonly children?: ReadonlyArray<FileNode>;
}

interface FileNodeEncoded {
  readonly id: string;
  readonly name: string;
  readonly is_directory: boolean;
  readonly children?: ReadonlyArray<FileNodeEncoded>;
}

export const FileNodeSchema: Schema.Schema<FileNode, FileNodeEncoded> =
  Schema.Struct({
    id: Schema.String,
    name: Schema.String,
    is_directory: Schema.Boolean,
    children: Schema.optional(
      Schema.Array(
        Schema.suspend(
          (): Schema.Schema<FileNode, FileNodeEncoded> => FileNodeSchema,
        ),
      ),
    ),
  });

export const FileSystemSchema = Schema.Array(FileNodeSchema);
export type FileSystemSchema = typeof FileSystemSchema.Type;

export const PreparedSessionSchema = Schema.Struct({
  id: Schema.String,
  name: Schema.String,
  status: Schema.String,
});
export type PreparedSessionSchema = typeof PreparedSessionSchema.Type;

export const SessionCreateSchema = Schema.Struct({
  name: Schema.String,
  template_id: Schema.String,
  environment_id: Schema.String,
  hcl_content: Schema.optional(Schema.String),
  nomad_artifacts: Schema.optional(Schema.Array(Schema.Unknown)),
});
export type SessionCreateSchema = typeof SessionCreateSchema.Type;

export const SessionResponseSchema = Schema.Struct({
  session_id: Schema.String,
  template_id: Schema.String,
  status: Schema.String,
  base_url: Schema.String,
});
export type SessionResponseSchema = typeof SessionResponseSchema.Type;

export const PlayerRoleUpdateSchema = Schema.Struct({
  role: Schema.String,
});

export const PlayerReadyUpdateSchema = Schema.Struct({
  is_ready: Schema.Boolean,
});

export const PreparedSessionsSchema = Schema.Array(PreparedSessionSchema);
export type PreparedSessionsSchema = typeof PreparedSessionsSchema.Type;

export const ConsulSessionsSchema = Schema.Record({
  key: Schema.String,
  value: Schema.String,
});
export type ConsulSessionsSchema = typeof ConsulSessionsSchema.Type;

const ConsulStatusToRunState: Record<string, string> = {
  passing: "RUNNING",
  critical: "STOPPED",
};

export const mergeSessionStatus = (
  sessions: PreparedSessionsSchema,
  consul: ConsulSessionsSchema,
): PreparedSessionsSchema =>
  sessions.map((sess) => ({
    ...sess,
    status: ConsulStatusToRunState[consul[sess.id]] ?? sess.status,
  }));

export const UploadFilePayloadSchema = Schema.Struct({
  project_id: Schema.String,
  name: Schema.String,
  parent_id: Schema.optional(Schema.String),
});
export type UploadFilePayloadSchema = typeof UploadFilePayloadSchema.Type;

export const CreateDirectoryPayloadSchema = Schema.Struct({
  project_id: Schema.String,
  name: Schema.String,
  parent_id: Schema.optional(Schema.String),
});
export type CreateDirectoryPayloadSchema =
  typeof CreateDirectoryPayloadSchema.Type;

export const WriteFileRawPayloadSchema = Schema.Struct({
  content: Schema.String,
  is_base64: Schema.Boolean,
});

export const UpdateFilePayloadSchema = Schema.Struct({
  name: Schema.optional(Schema.String),
  parent_id: Schema.optionalWith(Schema.NullOr(Schema.String), { exact: true }),
});
export type UpdateFilePayloadSchema = typeof UpdateFilePayloadSchema.Type;

export const ArtifactSelectionSchema = Schema.Struct({
  id: Schema.String,
  destination: Schema.String,
});
export type ArtifactSelectionSchema = typeof ArtifactSelectionSchema.Type;

export const LaunchNomadJobPayloadSchema = Schema.Struct({
  artifacts: Schema.Array(ArtifactSelectionSchema),
});

const idParam = HttpApiSchema.param("id", Schema.String);
const projectIdParam = HttpApiSchema.param("projectId", Schema.String);

const filesGroup = HttpApiGroup.make("Files")
  .add(
    HttpApiEndpoint.get("list")`/projects/${projectIdParam}/files`.addSuccess(
      FileSystemSchema,
    ),
  )
  .add(
    HttpApiEndpoint.post("upload")`/projects/${projectIdParam}/files/upload`
      .setPayload(
        HttpApiSchema.Multipart(
          Schema.Struct({
            file: Multipart.FilesSchema,
            name: Schema.String,
            parent_id: Schema.optional(Schema.String),
          }),
        ),
      )
      .addSuccess(FileNodeSchema),
  )
  .add(
    HttpApiEndpoint.post(
      "createDirectory",
    )`/projects/${projectIdParam}/files/directories`
      .setPayload(CreateDirectoryPayloadSchema)
      .addSuccess(FileNodeSchema),
  )
  .add(
    HttpApiEndpoint.get(
      "readRaw",
    )`/projects/${projectIdParam}/files/${idParam}/raw`.addSuccess(
      Schema.Uint8ArrayFromSelf.pipe(
        HttpApiSchema.withEncoding({
          kind: "Uint8Array",
          contentType: "application/octet-stream",
        }),
      ),
    ),
  )
  .add(
    HttpApiEndpoint.put(
      "writeRaw",
    )`/projects/${projectIdParam}/files/${idParam}/raw`
      .setPayload(
        Schema.Uint8ArrayFromSelf.pipe(
          HttpApiSchema.withEncoding({
            kind: "Uint8Array",
            contentType: "application/octet-stream",
          }),
        ),
      )
      .addSuccess(Schema.Unknown),
  )
  .add(
    HttpApiEndpoint.patch(
      "update",
    )`/projects/${projectIdParam}/files/${idParam}`
      .setPayload(UpdateFilePayloadSchema)
      .addSuccess(Schema.Unknown),
  )
  .add(
    HttpApiEndpoint.del(
      "delete",
    )`/projects/${projectIdParam}/files/${idParam}`.addSuccess(Schema.Unknown),
  );

const playerIdParam = HttpApiSchema.param("playerId", Schema.String);

const sessionsGroup = HttpApiGroup.make("Sessions")
  .add(
    HttpApiEndpoint.post("create", "/lobby")
      .setPayload(SessionCreateSchema)
      .addSuccess(SessionResponseSchema),
  )
  .add(
    HttpApiEndpoint.post("makePublic")`/lobby/${idParam}/public`.addSuccess(
      Schema.Unknown,
    ),
  )
  .add(
    HttpApiEndpoint.post("join")`/lobby/${idParam}/join`.addSuccess(
      Schema.Struct({ message: Schema.String, player_id: Schema.String }),
    ),
  )
  .add(
    HttpApiEndpoint.put(
      "updatePlayerReady",
    )`/lobby/${idParam}/players/${playerIdParam}/ready`
      .setPayload(PlayerReadyUpdateSchema)
      .addSuccess(Schema.Unknown),
  )
  .add(
    HttpApiEndpoint.put(
      "updatePlayerRole",
    )`/lobby/${idParam}/players/${playerIdParam}/role`
      .setPayload(PlayerRoleUpdateSchema)
      .addSuccess(Schema.Unknown),
  )
  .add(
    HttpApiEndpoint.get("list", "/lobby/sessions").addSuccess(
      PreparedSessionsSchema,
    ),
  )
  .add(
    HttpApiEndpoint.get("consulStatus", "/nomad/consul-sessions").addSuccess(
      ConsulSessionsSchema,
    ),
  )
  .add(
    HttpApiEndpoint.post("start")`/lobby/${idParam}/start`.addSuccess(
      Schema.Unknown,
    ),
  )
  .add(
    HttpApiEndpoint.post("stop")`/lobby/${idParam}/stop`.addSuccess(
      Schema.Unknown,
    ),
  );

const nomadGroup = HttpApiGroup.make("Nomad").add(
  HttpApiEndpoint.post("launch")`/nomad/${idParam}/launch`
    .setPayload(LaunchNomadJobPayloadSchema)
    .addSuccess(Schema.Unknown),
);

export class LobbyApi extends HttpApi.make("LobbyApi")
  .add(filesGroup)
  .add(sessionsGroup)
  .add(nomadGroup) {}

export class LobbyService extends Context.Tag("LobbyService")<
  LobbyService,
  {
    readonly createSession: (
      payload: SessionCreateSchema,
    ) => Effect.Effect<SessionResponseSchema, LobbyError>;
    readonly makeSessionPublic: (
      sessionId: string,
    ) => Effect.Effect<void, LobbyError>;
    readonly joinSession: (
      sessionId: string,
    ) => Effect.Effect<{ message: string; player_id: string }, LobbyError>;
    readonly updatePlayerReady: (
      sessionId: string,
      playerId: string,
      isReady: boolean,
    ) => Effect.Effect<void, LobbyError>;
    readonly updatePlayerRole: (
      sessionId: string,
      playerId: string,
      role: string,
    ) => Effect.Effect<void, LobbyError>;
    readonly fetchFileSystem: (
      projectId: string,
    ) => Effect.Effect<FileSystemSchema, LobbyError>;
    readonly fetchSessions: Effect.Effect<PreparedSessionsSchema, LobbyError>;
    readonly startSession: (
      workflowId: string,
    ) => Effect.Effect<void, LobbyError>;
    readonly stopSession: (
      workflowId: string,
    ) => Effect.Effect<void, LobbyError>;
    readonly uploadFile: (
      projectId: string,
      file: File,
      name: string,
      parentId: string | null,
    ) => Effect.Effect<FileNode, LobbyError>;
    readonly createDirectory: (
      projectId: string,
      name: string,
      parentId: string | null,
    ) => Effect.Effect<FileNode, LobbyError>;
    readonly readFileRaw: (
      projectId: string,
      id: string,
    ) => Effect.Effect<Uint8Array, LobbyError>;
    readonly writeFileRaw: (
      projectId: string,
      id: string,
      content: Uint8Array,
    ) => Effect.Effect<void, LobbyError>;
    readonly renameItem: (
      projectId: string,
      id: string,
      name: string,
    ) => Effect.Effect<void, LobbyError>;
    readonly moveItem: (
      projectId: string,
      id: string,
      parentId: string | null,
    ) => Effect.Effect<void, LobbyError>;
    readonly deleteItem: (
      projectId: string,
      id: string,
    ) => Effect.Effect<void, LobbyError>;
    readonly launchNomadJob: (
      fileId: string,
      artifacts: ReadonlyArray<ArtifactSelectionSchema>,
    ) => Effect.Effect<void, LobbyError>;
  }
>() {}

export const LobbyServiceLive = Layer.scoped(
  LobbyService,
  Effect.gen(function* () {
    const { apiUrl } = (yield* ConfigService).config;

    const authenticatedHttpClient = (yield* HttpClient.HttpClient).pipe(
      HttpClient.mapRequestEffect((req) =>
        Effect.promise(async () => {
          if (kc && kc.token) {
            try {
              await kc.updateToken(30);
            } catch (err) {
              kc.login();
            }
          }
          return kc?.token ?? "";
        }).pipe(
          Effect.map((token) => HttpClientRequest.bearerToken(token)(req)),
        ),
      ),
    );

    const client = yield* HttpApiClient.make(LobbyApi, {
      baseUrl: apiUrl,
    }).pipe(
      Effect.provideService(HttpClient.HttpClient, authenticatedHttpClient),
    );

    const withErrors = (endpoint: string) =>
      Effect.catchAll((e: unknown) =>
        Effect.fail(new LobbyHttpError({ message: String(e), endpoint })),
      );

    return {
      createSession: (payload) =>
        client.Sessions.create({ payload }).pipe(withErrors("POST /lobby")),

      makeSessionPublic: (sessionId) =>
        client.Sessions.makePublic({ path: { id: sessionId } }).pipe(
          Effect.asVoid,
          withErrors(`POST /lobby/${sessionId}/public`),
        ),

      joinSession: (sessionId) =>
        client.Sessions.join({ path: { id: sessionId } }).pipe(
          withErrors(`POST /lobby/${sessionId}/join`),
        ),

      updatePlayerReady: (sessionId, playerId, is_ready) =>
        client.Sessions.updatePlayerReady({
          path: { id: sessionId, playerId },
          payload: { is_ready },
        }).pipe(
          Effect.asVoid,
          withErrors(`PUT /lobby/${sessionId}/players/${playerId}/ready`),
        ),

      updatePlayerRole: (sessionId, playerId, role) =>
        client.Sessions.updatePlayerRole({
          path: { id: sessionId, playerId },
          payload: { role },
        }).pipe(
          Effect.asVoid,
          withErrors(`PUT /lobby/${sessionId}/players/${playerId}/role`),
        ),

      fetchFileSystem: (projectId) =>
        client.Files.list({ path: { projectId } }).pipe(
          withErrors(`GET /projects/${projectId}/files`),
        ),

      fetchSessions: Effect.gen(function* () {
        const [sessions, consul] = yield* Effect.all(
          [client.Sessions.list(), client.Sessions.consulStatus()],
          { concurrency: 2 },
        );
        return mergeSessionStatus(sessions, consul);
      }).pipe(withErrors("GET /lobby/sessions")),

      startSession: (workflowId) =>
        client.Sessions.start({ path: { id: workflowId } }).pipe(
          Effect.asVoid,
          withErrors(`POST /lobby/${workflowId}/start`),
        ),

      stopSession: (workflowId) =>
        client.Sessions.stop({ path: { id: workflowId } }).pipe(
          Effect.asVoid,
          withErrors(`POST /lobby/${workflowId}/stop`),
        ),

      uploadFile: (projectId, file, name, parentId) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("name", name);
        if (parentId != null) formData.append("parent_id", parentId);

        const req = HttpClientRequest.post(
          `${apiUrl}/projects/${projectId}/files/upload`,
        ).pipe(HttpClientRequest.bodyFormData(formData));

        return authenticatedHttpClient.execute(req).pipe(
          Effect.flatMap(HttpClientResponse.filterStatusOk),
          Effect.flatMap((res) => res.json),
          Effect.flatMap(Schema.decodeUnknown(FileNodeSchema)),
          withErrors(`POST /projects/${projectId}/files/upload`),
          Effect.scoped,
        );
      },

      createDirectory: (projectId, name, parentId) =>
        client.Files.createDirectory({
          path: { projectId },
          payload: {
            project_id: projectId,
            name,
            parent_id: parentId ?? undefined,
          },
        }).pipe(withErrors(`POST /projects/${projectId}/files/directories`)),

      readFileRaw: (projectId, id) =>
        client.Files.readRaw({ path: { projectId, id } }).pipe(
          withErrors(`GET /projects/${projectId}/files/${id}/raw`),
        ),

      writeFileRaw: (projectId, id, content: Uint8Array) =>
        client.Files.writeRaw({
          path: { projectId, id },
          payload: content,
        }).pipe(
          Effect.asVoid,
          withErrors(`PUT /projects/${projectId}/files/${id}/raw`),
        ),

      renameItem: (projectId, id, name) =>
        client.Files.update({
          path: { projectId, id },
          payload: { name },
        }).pipe(
          Effect.asVoid,
          withErrors(`PATCH /projects/${projectId}/files/${id}`),
        ),

      moveItem: (projectId, id, parentId) =>
        client.Files.update({
          path: { projectId, id },
          payload: { parent_id: parentId },
        }).pipe(
          Effect.asVoid,
          withErrors(`PATCH /projects/${projectId}/files/${id}`),
        ),

      deleteItem: (projectId, id) =>
        client.Files.delete({ path: { projectId, id } }).pipe(
          Effect.asVoid,
          withErrors(`DELETE /projects/${projectId}/files/${id}`),
        ),

      launchNomadJob: (fileId, artifacts) =>
        client.Nomad.launch({
          path: { id: fileId },
          payload: { artifacts },
        }).pipe(Effect.asVoid, withErrors(`POST /nomad/${fileId}/launch`)),
    };
  }),
).pipe(
  Layer.provide(FetchHttpClient.layer),
  Layer.withSpan("LobbyServiceLive.Initialize"),
);
