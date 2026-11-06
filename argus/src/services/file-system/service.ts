/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { open } from "@tauri-apps/plugin-dialog";
import { mkdir, readDir, readFile, readTextFile, writeFile } from "@tauri-apps/plugin-fs";
import { Context, Effect, Layer } from "effect";

declare global {
  interface OpenFilePickerOptions {
    multiple?: boolean;
    types?: Array<{
      description?: string;
      accept?: Record<string, string[]>;
    }>;
  }

  interface DirectoryPickerOptions {
    startIn?: string | FileSystemHandle;
  }

  interface FileSystemDirectoryHandle {
    values(): AsyncIterableIterator<FileSystemDirectoryHandle | FileSystemFileHandle>;
    entries(): AsyncIterableIterator<[string, FileSystemDirectoryHandle | FileSystemFileHandle]>;
    keys(): AsyncIterableIterator<string>;
    [Symbol.asyncIterator](): AsyncIterableIterator<[string, FileSystemDirectoryHandle | FileSystemFileHandle]>;
  }

  interface Window {
    showDirectoryPicker(options?: DirectoryPickerOptions): Promise<FileSystemDirectoryHandle>;
    showOpenFilePicker(options?: OpenFilePickerOptions): Promise<FileSystemFileHandle[]>;
  }
}

export class UserAbortError {
  readonly _tag = "UserAbortError";
  constructor(readonly message = "The user aborted a request.") {}
}

export class FileSystemIoError {
  readonly _tag = "FileSystemIoError";
  constructor(readonly cause: unknown) {}
}

export class EffectFileHandle implements Partial<FileSystemFileHandle> {
  readonly kind = "file" as const;

  constructor(
    readonly name: string,
    readonly fullPath: string,
  ) {}

  async isSameEntry(other: FileSystemHandle): Promise<boolean> {
    return other instanceof EffectFileHandle && other.fullPath === this.fullPath;
  }

  async getFile(): Promise<File> {
    const fullPath = this.fullPath;
    const file = new File([], this.name);

    Object.defineProperty(file, "text", {
      value: async () => readTextFile(fullPath),
      writable: true,
      configurable: true,
    });

    Object.defineProperty(file, "arrayBuffer", {
      value: async () => {
        const bytes = await readFile(fullPath);
        return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
      },
      writable: true,
      configurable: true,
    });

    Object.defineProperty(file, "path", {
      value: fullPath,
      writable: false,
    });
    return file;
  }

  async createWritable(): Promise<FileSystemWritableFileStream> {
    const fullPath = this.fullPath;
    let chunks: Uint8Array[] = [];

    const underlyingSink: UnderlyingSink<any> = {
      async write(chunk) {
        if (typeof chunk === "string") {
          chunks.push(new TextEncoder().encode(chunk));
        } else if (chunk instanceof ArrayBuffer) {
          chunks.push(new Uint8Array(chunk));
        } else if (ArrayBuffer.isView(chunk)) {
          chunks.push(new Uint8Array(chunk.buffer, chunk.byteOffset, chunk.byteLength));
        } else if (chunk instanceof Blob) {
          chunks.push(new Uint8Array(await chunk.arrayBuffer()));
        } else if (chunk && typeof chunk === "object" && "data" in chunk) {
          // FileSystemWriteChunkType object { type: 'write', data: ... }
          const data = chunk.data;
          if (typeof data === "string") {
            chunks.push(new TextEncoder().encode(data));
          } else if (data instanceof ArrayBuffer) {
            chunks.push(new Uint8Array(data));
          } else if (ArrayBuffer.isView(data)) {
            chunks.push(new Uint8Array(data.buffer, data.byteOffset, data.byteLength));
          } else if (data instanceof Blob) {
            chunks.push(new Uint8Array(await data.arrayBuffer()));
          }
        }
      },
      async close() {
        const totalLength = chunks.reduce((acc, c) => acc + c.byteLength, 0);
        const merged = new Uint8Array(totalLength);
        let offset = 0;
        for (const c of chunks) {
          merged.set(c, offset);
          offset += c.byteLength;
        }
        await writeFile(fullPath, merged);
      },
      abort() {
        chunks = [];
      },
    };

    const stream = new WritableStream(underlyingSink) as unknown as FileSystemWritableFileStream;
    return stream;
  }
}

/** Rejects the names the File System Access API rejects: empty, ".", ".." or containing a separator. */
function assertValidEntryName(name: string): void {
  if (!name || name === "." || name === ".." || /[\\/]/.test(name)) {
    throw new TypeError(`Name is not allowed: ${name}`);
  }
}

export class EffectDirectoryHandle implements Partial<FileSystemDirectoryHandle> {
  readonly kind = "directory" as const;

  constructor(
    readonly name: string,
    readonly fullPath: string,
  ) {}

  async isSameEntry(other: FileSystemHandle): Promise<boolean> {
    return other instanceof EffectDirectoryHandle && other.fullPath === this.fullPath;
  }

  async *values(): AsyncIterableIterator<EffectDirectoryHandle | EffectFileHandle> {
    const entries = await readDir(this.fullPath);
    for (const entry of entries) {
      const sep = this.fullPath.includes("\\") ? "\\" : "/";
      const childPath = `${this.fullPath.replace(/[\\/]+$/, "")}${sep}${entry.name}`;

      if (entry.isDirectory) {
        yield new EffectDirectoryHandle(entry.name, childPath);
      } else if (entry.isFile) {
        yield new EffectFileHandle(entry.name, childPath);
      }
    }
  }

  async *entries(): AsyncIterableIterator<[string, EffectDirectoryHandle | EffectFileHandle]> {
    for await (const handle of this.values()) {
      yield [handle.name, handle];
    }
  }

  async *keys(): AsyncIterableIterator<string> {
    for await (const [key] of this.entries()) {
      yield key;
    }
  }

  [Symbol.asyncIterator](): AsyncIterableIterator<[string, EffectDirectoryHandle | EffectFileHandle]> {
    return this.entries();
  }

  private childPath(name: string): string {
    const sep = this.fullPath.includes("\\") ? "\\" : "/";
    return `${this.fullPath.replace(/[\\/]+$/, "")}${sep}${name}`;
  }

  /** The entry `name` of this directory, or undefined if there is none. */
  private async findEntry(name: string) {
    const entries = await readDir(this.fullPath);
    return entries.find((entry) => entry.name === name);
  }

  // As in the File System Access API: `name` is a single entry name (no
  // separator, no ".."), a missing entry is a NotFoundError unless
  // `create` is set, and an entry of the other kind is a TypeMismatchError.
  // Symlinks are accepted as either kind, as readDir does not tell their target.
  async getDirectoryHandle(
    name: string,
    options?: FileSystemGetDirectoryOptions,
  ): Promise<EffectDirectoryHandle> {
    assertValidEntryName(name);
    const entry = await this.findEntry(name);
    if (!entry) {
      if (!options?.create) {
        throw new DOMException(`${name} not found in ${this.fullPath}`, "NotFoundError");
      }
      await mkdir(this.childPath(name));
    } else if (!entry.isDirectory && !entry.isSymlink) {
      throw new DOMException(`${name} in ${this.fullPath} is not a directory`, "TypeMismatchError");
    }
    return new EffectDirectoryHandle(name, this.childPath(name));
  }

  async getFileHandle(
    name: string,
    options?: FileSystemGetFileOptions,
  ): Promise<EffectFileHandle> {
    assertValidEntryName(name);
    const entry = await this.findEntry(name);
    if (!entry) {
      if (!options?.create) {
        throw new DOMException(`${name} not found in ${this.fullPath}`, "NotFoundError");
      }
      await writeFile(this.childPath(name), new Uint8Array());
    } else if (!entry.isFile && !entry.isSymlink) {
      throw new DOMException(`${name} in ${this.fullPath} is not a file`, "TypeMismatchError");
    }
    return new EffectFileHandle(name, this.childPath(name));
  }

  async removeEntry(_name: string): Promise<void> {
    throw new DOMException("removeEntry is not implemented", "NotSupportedError");
  }

  async resolve(_possibleDescendant: FileSystemHandle): Promise<string[] | null> {
    throw new DOMException("resolve is not implemented", "NotSupportedError");
  }
}

export class FileSystemService extends Context.Tag("FileSystemService")<
  FileSystemService,
  {
    readonly showOpenFilePicker: (
      options?: OpenFilePickerOptions,
    ) => Effect.Effect<FileSystemFileHandle[], UserAbortError | FileSystemIoError>;
    readonly showDirectoryPicker: (
      options?: DirectoryPickerOptions,
    ) => Effect.Effect<FileSystemDirectoryHandle, UserAbortError | FileSystemIoError>;
  }
>() {}

export const FileSystemLive = Layer.succeed(
  FileSystemService,
  FileSystemService.of({
    showOpenFilePicker: (options) =>
      Effect.gen(function* () {
        yield* Effect.logDebug("Opening file picker dialog");

        const filters: Array<{ name: string; extensions: string[] }> = [];
        if (options?.types) {
          for (const t of options.types) {
            const extensions: string[] = [];
            if (t.accept) {
              for (const extList of Object.values(t.accept)) {
                for (const ext of extList) {
                  extensions.push(ext.replace(/^\./, ""));
                }
              }
            }
            filters.push({
              name: t.description || "Files",
              extensions,
            });
          }
        }

        const selected = yield* Effect.tryPromise({
          try: () =>
            open({
              multiple: options?.multiple ?? false,
              directory: false,
              filters: filters.length > 0 ? filters : undefined,
            }),
          catch: (cause) => new FileSystemIoError(cause),
        });

        if (!selected) {
          yield* Effect.logDebug("File picker dialog aborted by user");
          return yield* Effect.fail(new UserAbortError());
        }

        const paths = Array.isArray(selected) ? selected : [selected];
        yield* Effect.annotateCurrentSpan({ "files.count": paths.length });

        return paths.map((p) => {
          const name = p.split(/[\\/]/).filter(Boolean).pop() || "";
          return new EffectFileHandle(name, p) as unknown as FileSystemFileHandle;
        });
      }).pipe(
        Effect.withSpan("FileSystem.ShowOpenFilePicker", {
          attributes: { multiple: options?.multiple ?? false },
        }),
      ),

    showDirectoryPicker: (options) =>
      Effect.gen(function* () {
        yield* Effect.logDebug("Opening directory picker dialog");

        let dirPath: string | null = null;
        if (typeof options?.startIn === "string" && options.startIn) {
          dirPath = options.startIn;
        } else {
          const selected = yield* Effect.tryPromise({
            try: () => open({ directory: true, multiple: false }),
            catch: (cause) => new FileSystemIoError(cause),
          });
          if (typeof selected === "string") {
            dirPath = selected;
          }
        }

        if (!dirPath) {
          yield* Effect.logDebug("Directory picker dialog aborted by user");
          return yield* Effect.fail(new UserAbortError());
        }

        const name = dirPath.split(/[\\/]/).filter(Boolean).pop() || "root";
        yield* Effect.annotateCurrentSpan({ "directory.path": dirPath });

        return new EffectDirectoryHandle(name, dirPath) as unknown as FileSystemDirectoryHandle;
      }).pipe(
        Effect.withSpan("FileSystem.ShowDirectoryPicker", {
          attributes: {
            hasStartIn: typeof options?.startIn === "string",
          },
        }),
      ),
  }),
);
