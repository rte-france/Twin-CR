/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { Effect, Layer, Context, Schema } from "effect";
import {
  HttpApi,
  HttpApiEndpoint,
  HttpApiGroup,
  HttpApiSchema,
  HttpApiClient,
  HttpClient,
  HttpClientRequest,
  FetchHttpClient,
} from "@effect/platform";
import { ConfigService } from "@/services/config";
import { kc } from "@/features/auth";

export class ProjectHttpError extends Schema.TaggedError<ProjectHttpError>()(
  "ProjectHttpError",
  {
    message: Schema.String,
    endpoint: Schema.String,
    cause: Schema.optional(Schema.Unknown),
  },
) {}

export const GroupSchema = Schema.Struct({
  id: Schema.UUID,
  name: Schema.String,
  parent_id: Schema.NullOr(Schema.UUID),
});

const GroupCreateSchema = Schema.Struct({
  name: Schema.String,
  parent_id: Schema.optional(Schema.NullOr(Schema.UUID)),
});

export const ProjectSchema = Schema.Struct({
  id: Schema.UUID,
  name: Schema.String,
  group_id: Schema.UUID,
});

const ProjectCreateSchema = Schema.Struct({
  name: Schema.String,
  group_id: Schema.UUID,
});
const ProjectUpdateSchema = Schema.Struct({
  name: Schema.optional(Schema.NullOr(Schema.String)),
  group_id: Schema.optional(Schema.NullOr(Schema.UUID)),
});

const ProjectDuplicateSchema = Schema.Struct({
  target_group_id: Schema.UUID,
});

const ShareSchema = Schema.Struct({
  target_user_id: Schema.String,
  role: Schema.String,
});
const idParam = HttpApiSchema.param("id", Schema.UUID);

const groupsGroup = HttpApiGroup.make("Groups")
  .add(
    HttpApiEndpoint.get("list", "/groups").addSuccess(
      Schema.Array(GroupSchema),
    ),
  )
  .add(
    HttpApiEndpoint.post("create", "/groups")
      .setPayload(GroupCreateSchema)
      .addSuccess(GroupSchema),
  )
  .add(
    HttpApiEndpoint.del("delete")`/groups/${idParam}`.addSuccess(
      Schema.Unknown,
    ),
  )
  .add(
    HttpApiEndpoint.post("share")`/groups/${idParam}/share`
      .setPayload(ShareSchema)
      .addSuccess(Schema.Unknown),
  );

const projectsGroup = HttpApiGroup.make("Projects")
  .add(
    HttpApiEndpoint.get("list", "/projects").addSuccess(
      Schema.Array(ProjectSchema),
    ),
  )
  .add(
    HttpApiEndpoint.post("create", "/projects")
      .setPayload(ProjectCreateSchema)
      .addSuccess(ProjectSchema),
  )
  .add(
    HttpApiEndpoint.patch("update")`/projects/${idParam}`
      .setPayload(ProjectUpdateSchema)
      .addSuccess(Schema.Unknown),
  )
  .add(
    HttpApiEndpoint.del("delete")`/projects/${idParam}`.addSuccess(
      Schema.Unknown,
    ),
  )
  .add(
    HttpApiEndpoint.post("duplicate")`/projects/${idParam}/duplicate`
      .setPayload(ProjectDuplicateSchema)
      .addSuccess(ProjectSchema),
  );

export class ProjectApi extends HttpApi.make("ProjectApi")
  .add(groupsGroup)
  .add(projectsGroup) {}

export class ProjectService extends Context.Tag("ProjectService")<
  ProjectService,
  {
    fetchGroups: Effect.Effect<
      readonly (typeof GroupSchema.Type)[],
      ProjectHttpError
    >;
    createGroup: (
      name: string,
      parentId?: string | null,
    ) => Effect.Effect<typeof GroupSchema.Type, ProjectHttpError>;
    deleteGroup: (id: string) => Effect.Effect<void, ProjectHttpError>;
    shareGroup: (
      groupId: string,
      targetUserId: string,
      role: string,
    ) => Effect.Effect<void, ProjectHttpError>;
    fetchProjects: Effect.Effect<
      readonly (typeof ProjectSchema.Type)[],
      ProjectHttpError
    >;
    createProject: (
      name: string,
      groupId: string,
    ) => Effect.Effect<typeof ProjectSchema.Type, ProjectHttpError>;
    updateProject: (
      id: string,
      name?: string | null,
      groupId?: string | null,
    ) => Effect.Effect<void, ProjectHttpError>;
    deleteProject: (id: string) => Effect.Effect<void, ProjectHttpError>;
    duplicateProject: (
      id: string,
      targetGroupId: string,
    ) => Effect.Effect<typeof ProjectSchema.Type, ProjectHttpError>;
  }
>() {}

export const ProjectServiceLive = Layer.scoped(
  ProjectService,
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

    const client = yield* HttpApiClient.make(ProjectApi, {
      baseUrl: apiUrl,
    }).pipe(
      Effect.provideService(HttpClient.HttpClient, authenticatedHttpClient),
    );

    const withErrors = (endpoint: string) =>
      Effect.catchAll((e: unknown) =>
        Effect.fail(new ProjectHttpError({ message: String(e), endpoint })),
      );

    return {
      fetchGroups: client.Groups.list().pipe(withErrors("GET /groups")),
      createGroup: (name, parentId) =>
        client.Groups.create({
          payload: { name, parent_id: parentId || null },
        }).pipe(withErrors("POST /groups")),
      deleteGroup: (id) =>
        client.Groups.delete({ path: { id } }).pipe(
          Effect.asVoid,
          withErrors(`DELETE /groups/${id}`),
        ),
      shareGroup: (groupId, targetUserId, role) =>
        client.Groups.share({
          path: { id: groupId },
          payload: { target_user_id: targetUserId, role },
        }).pipe(Effect.asVoid, withErrors(`POST /groups/${groupId}/share`)),
      fetchProjects: client.Projects.list().pipe(withErrors("GET /projects")),
      createProject: (name, group_id) =>
        client.Projects.create({ payload: { name, group_id } }).pipe(
          withErrors("POST /projects"),
        ),
      updateProject: (id, name, group_id) =>
        client.Projects.update({
          path: { id },
          payload: { name, group_id },
        }).pipe(Effect.asVoid, withErrors(`PATCH /projects/${id}`)),
      deleteProject: (id) =>
        client.Projects.delete({ path: { id } }).pipe(
          Effect.asVoid,
          withErrors(`DELETE /projects/${id}`),
        ),
      duplicateProject: (id, target_group_id) =>
        client.Projects.duplicate({
          path: { id },
          payload: { target_group_id },
        }).pipe(withErrors(`POST /projects/${id}/duplicate`)),
    };
  }),
).pipe(
  Layer.provide(FetchHttpClient.layer),
  Layer.withSpan("ProjectServiceLive.Initialize"),
);
