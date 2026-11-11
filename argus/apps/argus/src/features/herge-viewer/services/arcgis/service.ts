/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { Context, Effect, Schema, Layer, Ref } from "effect";

import { type ArcGisError, ArcGisParseError, ArcGisCacheError } from "./error";
import {
  IdentifyResponseSchema,
  LegendResponseSchema,
  QueryFeaturesSchema,
} from "./domain";

import type { Extent, LegendLayer } from "../../types";
import { HergeClient } from "@/services/herge";

export class ArcGisService extends Context.Tag("ArcGisService")<
  ArcGisService,
  {
    readonly fetchLegend: (
      serviceId: string,
    ) => Effect.Effect<readonly LegendLayer[], ArcGisError>;

    readonly fetchMapImage: (
      serviceId: string,
      ext: Extent,
      width: number,
      height: number,
      defExpr?: string,
    ) => Effect.Effect<string, ArcGisError>;

    readonly fetchSchemasList: Effect.Effect<readonly string[], ArcGisError>;

    readonly fetchIdentify: (
      serviceId: string,
      x: number,
      y: number,
      ext: Extent,
      width: number,
      height: number,
    ) => Effect.Effect<readonly any[], ArcGisError>;

    readonly fetchSchemaExtent: (
      schemaName: string,
    ) => Effect.Effect<Extent | null, ArcGisError>;
  }
>() {}

type Url = string;
type ObjectUrl = string;

export const ArcGisServiceLive = Layer.scoped(
  ArcGisService,
  Effect.gen(function* () {
    const hergeClient = yield* HergeClient;
    const imageCache = yield* Ref.make(new Map<Url, ObjectUrl>());

    yield* Effect.acquireRelease(Effect.void, () =>
      Effect.gen(function* () {
        const cache = yield* Ref.get(imageCache);
        cache.forEach((url) => URL.revokeObjectURL(url));
      }),
    );

    const decodeJson = <A, I>(
      schema: Schema.Schema<A, I>,
      rawData: Uint8Array,
    ) =>
      Effect.gen(function* () {
        const text = new TextDecoder().decode(rawData);
        const json = yield* Effect.try({
          try: () => JSON.parse(text),
          catch: (e) =>
            new ArcGisParseError({
              message: `Invalid JSON: ${JSON.stringify(e)}`,
            }),
        });

        const decode = Schema.decodeUnknown(schema);
        return yield* decode(json).pipe(
          Effect.catchTag("ParseError", (e) =>
            Effect.fail(new ArcGisParseError({ message: e.message })),
          ),
        );
      });

    return {
      fetchLegend: (serviceId) =>
        Effect.gen(function* () {
          const url = `/${serviceId}/MapServer/legend?f=json`;
          const rawData = yield* hergeClient.fetch(url);
          const data = yield* decodeJson(LegendResponseSchema, rawData);
          return data.layers as any[];
        }),

      fetchMapImage: (serviceId, ext, width, height, defExpr) =>
        Effect.gen(function* () {
          const params = new URLSearchParams({
            bbox: `${ext.xmin},${ext.ymin},${ext.xmax},${ext.ymax}`,
            size: `${width},${height}`,
            format: "png32",
            transparent: "true",
            f: "image",
          });

          if (defExpr && serviceId === "SCHEMAS") {
            params.append("layerDefs", JSON.stringify({ "0": defExpr }));
          }

          const url = `/${serviceId}/MapServer/export?${params.toString()}`;

          const cache = yield* Ref.get(imageCache);
          if (cache.has(url)) return cache.get(url)!;

          const rawData = yield* hergeClient.fetch(url);

          const objectUrl = yield* Effect.try({
            try: () => {
              const blob = new Blob([rawData], { type: "image/png" });
              return URL.createObjectURL(blob);
            },
            catch: (e) =>
              new ArcGisCacheError({
                message: `Failed to create Blob: ${JSON.stringify(e)}`,
              }),
          });

          yield* Ref.update(imageCache, (currentCache) => {
            const newCache = new Map(currentCache);
            if (newCache.size > 40) {
              const oldestUrl = newCache.keys().next().value;
              if (oldestUrl) {
                URL.revokeObjectURL(newCache.get(oldestUrl)!);
                newCache.delete(oldestUrl);
              }
            }
            newCache.set(url, objectUrl);
            return newCache;
          });

          return objectUrl;
        }),

      fetchSchemasList: Effect.gen(function* () {
        const url =
          `/SCHEMAS/MapServer/0/query?` +
          new URLSearchParams({
            where: "1=1",
            outFields: "NOM_SCHEMA",
            returnGeometry: "false",
            returnDistinctValues: "true",
            orderByFields: "NOM_SCHEMA",
            f: "json",
          }).toString();

        const rawData = yield* hergeClient.fetch(url);
        const data = yield* decodeJson(QueryFeaturesSchema, rawData);

        return data.features
          .map((f) => f.attributes.NOM_SCHEMA || f.attributes.NOM)
          .filter((name) => !!name);
      }),

      fetchIdentify: (serviceId, x, y, ext, width, height) =>
        Effect.gen(function* () {
          const params = new URLSearchParams({
            geometry: `${x},${y}`,
            geometryType: "esriGeometryPoint",
            sr: "2154",
            layers: "visible",
            tolerance: "15",
            mapExtent: `${ext.xmin},${ext.ymin},${ext.xmax},${ext.ymax}`,
            imageDisplay: `${width},${height},96`,
            returnGeometry: "true",
            f: "json",
          });
          const url = `/${serviceId}/MapServer/identify?${params.toString()}`;
          const rawData = yield* hergeClient.fetch(url);
          const data = yield* decodeJson(IdentifyResponseSchema, rawData);
          return data.results || [];
        }),

      fetchSchemaExtent: (schemaName) =>
        Effect.gen(function* () {
          const safeName = schemaName.replace(/'/g, "''");

          const url =
            `/SCHEMAS/MapServer/0/query?` +
            new URLSearchParams({
              where: `NOM_SCHEMA = '${safeName}' OR NOM = '${safeName}'`,
              returnGeometry: "true",
              outSR: "2154",
              f: "json",
            }).toString();

          const rawData = yield* hergeClient.fetch(url);
          const text = new TextDecoder().decode(rawData);
          const data = JSON.parse(text);

          if (data.features && data.features.length > 0) {
            const geometry = data.features[0].geometry;

            if (geometry && geometry.rings && geometry.rings.length > 0) {
              const xs = geometry.rings[0].map((pt: number[]) => pt[0]);
              const ys = geometry.rings[0].map((pt: number[]) => pt[1]);

              return {
                xmin: Math.min(...xs),
                xmax: Math.max(...xs),
                ymin: Math.min(...ys),
                ymax: Math.max(...ys),
              };
            }
          }

          console.warn(
            `[Warning] Aucune emprise trouvée pour le schéma : ${schemaName}`,
          );
          return null;
        }),
    };
  }),
);
