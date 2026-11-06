/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect, vi } from "vitest";
import fc from "fast-check";
import { Effect } from "effect";
import {
  FileSystemService,
  FileSystemLive,
  EffectFileHandle,
  EffectDirectoryHandle,
} from "@/services/file-system";
import * as tauriDialog from "@tauri-apps/plugin-dialog";
import * as tauriFs from "@tauri-apps/plugin-fs";

vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: vi.fn(),
}));

vi.mock("@tauri-apps/plugin-fs", () => ({
  mkdir: vi.fn(),
  readDir: vi.fn(),
  readFile: vi.fn(),
  readTextFile: vi.fn(),
  writeFile: vi.fn(),
}));

const dirEntry = (name: string, kind: "file" | "directory") =>
  ({
    name,
    isDirectory: kind === "directory",
    isFile: kind === "file",
    isSymlink: false,
  }) as any;

describe("FileSystem - Property-Based Testing", () => {
  const validFileNameArb = fc
    .stringMatching(/^[a-zA-Z0-9_-]{1,15}$/)
    .map((name) => `${name}.txt`);

  const pathSeparatorArb = fc.constantFrom("/", "\\");

  const fullPathArb = fc
    .tuple(
      fc.array(fc.stringMatching(/^[a-zA-Z0-9_-]{1,10}$/), { minLength: 1, maxLength: 4 }),
      validFileNameArb,
      pathSeparatorArb,
    )
    .map(([dirs, file, sep]) => `${dirs.join(sep)}${sep}${file}`);

  describe("EffectFileHandle Contract", () => {
    it("always produces a standard DOM File with immutable .path property matching fullPath", async () => {
      await fc.assert(
        fc.asyncProperty(
          validFileNameArb,
          fullPathArb,
          fc.string(),
          async (fileName, fullPath, fileContent) => {
            vi.mocked(tauriFs.readTextFile).mockReset();
            vi.mocked(tauriFs.readTextFile).mockResolvedValueOnce(fileContent);

            const handle = new EffectFileHandle(fileName, fullPath);
            const file = await handle.getFile();

            // Lazy reading: readTextFile shouldn't be called upon handle.getFile()
            expect(tauriFs.readTextFile).not.toHaveBeenCalled();

            expect(file).toBeInstanceOf(File);
            expect(file.name).toBe(fileName);
            expect((file as any).path).toBe(fullPath);
            expect(await file.text()).toBe(fileContent);
            expect(tauriFs.readTextFile).toHaveBeenCalledWith(fullPath);

            // Lazy binary reading via arrayBuffer()
            const rawBytes = new TextEncoder().encode(fileContent);
            vi.mocked(tauriFs.readFile).mockResolvedValueOnce(rawBytes);
            const buf = await file.arrayBuffer();
            expect(Array.from(new Uint8Array(buf))).toEqual(Array.from(rawBytes));
            expect(tauriFs.readFile).toHaveBeenCalledWith(fullPath);

            // Path must be read-only
            expect(() => {
              (file as any).path = "modified";
            }).toThrow();
          },
        ),
        { numRuns: 100 },
      );
    });

    it("correctly evaluates isSameEntry equivalence", async () => {
      await fc.assert(
        fc.asyncProperty(
          validFileNameArb,
          fullPathArb,
          fullPathArb,
          async (name, path1, path2) => {
            const h1 = new EffectFileHandle(name, path1);
            const h2 = new EffectFileHandle(name, path2);

            const same = await h1.isSameEntry(h2);
            expect(same).toBe(path1 === path2);
          },
        ),
        { numRuns: 50 },
      );
    });

    it("writable stream faithfully serializes arbitrary chunks to disk", async () => {
      await fc.assert(
        fc.asyncProperty(
          validFileNameArb,
          fullPathArb,
          fc.array(fc.uint8Array({ minLength: 0, maxLength: 128 }), { minLength: 1, maxLength: 5 }),
          async (name, fullPath, chunks) => {
            let writtenBytes: Uint8Array | null = null;
            vi.mocked(tauriFs.writeFile).mockImplementationOnce(async (_p, data) => {
              writtenBytes = data as Uint8Array;
            });

            const handle = new EffectFileHandle(name, fullPath);
            const writable = await handle.createWritable();
            const writer = writable.getWriter();

            for (const chunk of chunks) {
              await writer.write(chunk);
            }
            await writer.close();

            expect(writtenBytes).not.toBeNull();
            const totalExpected = chunks.reduce((acc, c) => acc + c.byteLength, 0);
            expect(writtenBytes!.byteLength).toBe(totalExpected);

            // Verify content byte-for-byte
            let offset = 0;
            for (const chunk of chunks) {
              expect(writtenBytes!.slice(offset, offset + chunk.byteLength)).toEqual(chunk);
              offset += chunk.byteLength;
            }
          },
        ),
        { numRuns: 50 },
      );
    });
  });

  describe("EffectDirectoryHandle Entry Lookup", () => {
    it("resolves existing child entries preserving the directory separator", async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.stringMatching(/^[a-zA-Z0-9_-]{1,8}$/),
          validFileNameArb,
          pathSeparatorArb,
          async (subdir, fileName, sep) => {
            const rootPath = `root${sep}dir`;
            const dirHandle = new EffectDirectoryHandle("dir", rootPath);
            vi.mocked(tauriFs.readDir).mockResolvedValue([
              dirEntry(subdir, "directory"),
              dirEntry(fileName, "file"),
            ]);

            const fileHandle = await dirHandle.getFileHandle(fileName);
            expect(fileHandle.name).toBe(fileName);
            expect(fileHandle.fullPath).toBe(`${rootPath}${sep}${fileName}`);

            const subHandle = await dirHandle.getDirectoryHandle(subdir);
            expect(subHandle.name).toBe(subdir);
            expect(subHandle.fullPath).toBe(`${rootPath}${sep}${subdir}`);
          },
        ),
        { numRuns: 50 },
      );
    });

    it("rejects names that are not a single entry name with TypeError", async () => {
      await fc.assert(
        fc.asyncProperty(
          fc.oneof(
            fc.constantFrom("", ".", ".."),
            fc
              .tuple(
                fc.stringMatching(/^[a-zA-Z0-9_.-]{0,8}$/),
                pathSeparatorArb,
                fc.stringMatching(/^[a-zA-Z0-9_.-]{0,8}$/),
              )
              .map(([a, sep, b]) => `${a}${sep}${b}`),
          ),
          async (name) => {
            const dirHandle = new EffectDirectoryHandle("root", "root");
            await expect(dirHandle.getFileHandle(name)).rejects.toBeInstanceOf(TypeError);
            await expect(dirHandle.getDirectoryHandle(name)).rejects.toBeInstanceOf(TypeError);
          },
        ),
        { numRuns: 50 },
      );
    });

    it("reports missing entries as NotFoundError unless create is set", async () => {
      await fc.assert(
        fc.asyncProperty(validFileNameArb, async (name) => {
          vi.mocked(tauriFs.readDir).mockResolvedValue([]);
          vi.mocked(tauriFs.mkdir).mockClear();
          vi.mocked(tauriFs.writeFile).mockClear();
          const dirHandle = new EffectDirectoryHandle("root", "root");

          await expect(dirHandle.getFileHandle(name)).rejects.toMatchObject({ name: "NotFoundError" });
          await expect(dirHandle.getDirectoryHandle(name)).rejects.toMatchObject({ name: "NotFoundError" });

          await dirHandle.getFileHandle(name, { create: true });
          expect(tauriFs.writeFile).toHaveBeenCalledWith(`root/${name}`, new Uint8Array());
          await dirHandle.getDirectoryHandle(name, { create: true });
          expect(tauriFs.mkdir).toHaveBeenCalledWith(`root/${name}`);
        }),
        { numRuns: 25 },
      );
    });

    it("reports an entry of the other kind as TypeMismatchError", async () => {
      vi.mocked(tauriFs.readDir).mockResolvedValue([
        dirEntry("sub", "directory"),
        dirEntry("a.txt", "file"),
      ]);
      const dirHandle = new EffectDirectoryHandle("root", "root");

      await expect(dirHandle.getFileHandle("sub")).rejects.toMatchObject({ name: "TypeMismatchError" });
      await expect(dirHandle.getDirectoryHandle("a.txt")).rejects.toMatchObject({ name: "TypeMismatchError" });
    });
  });

  describe("FileSystemService Effectful Layer", () => {
    it("maps dialog cancellation to UserAbortError without crashing", async () => {
      vi.mocked(tauriDialog.open).mockResolvedValueOnce(null);

      const result = await Effect.runPromiseExit(
        Effect.gen(function* () {
          const fs = yield* FileSystemService;
          return yield* fs.showOpenFilePicker();
        }).pipe(Effect.provide(FileSystemLive)),
      );

      expect(result._tag).toBe("Failure");
      if (result._tag === "Failure") {
        expect(result.cause.toString()).toContain("UserAbortError");
      }
    });

    it("maps unexpected dialog failures to FileSystemIoError", async () => {
      vi.mocked(tauriDialog.open).mockRejectedValueOnce(new Error("IPC failed"));

      const result = await Effect.runPromiseExit(
        Effect.gen(function* () {
          const fs = yield* FileSystemService;
          return yield* fs.showOpenFilePicker();
        }).pipe(Effect.provide(FileSystemLive)),
      );

      expect(result._tag).toBe("Failure");
      if (result._tag === "Failure") {
        expect(result.cause.toString()).toContain("FileSystemIoError");
      }
    });
  });
});
