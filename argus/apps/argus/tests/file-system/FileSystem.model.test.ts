/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { describe, it, expect, vi } from "vitest";
import fc from "fast-check";
import { EffectDirectoryHandle } from "@/services/file-system";
import * as tauriFs from "@tauri-apps/plugin-fs";

vi.mock("@tauri-apps/plugin-fs", () => ({
  mkdir: vi.fn(),
  readDir: vi.fn(),
  readTextFile: vi.fn(),
  writeFile: vi.fn(),
}));

/**
 * Model State of an in-memory Virtual File System (VFS).
 */
interface VfsNode {
  readonly kind: "file" | "directory";
  readonly name: string;
  content?: string; // only for files
  children?: Map<string, VfsNode>; // only for directories
}

interface FsModel {
  root: VfsNode;
}

interface SUT {
  rootHandle: EffectDirectoryHandle;
  vfsData: Map<string, { kind: "file" | "directory"; content?: string }>;
}

function normalizePath(p: string): string {
  return p.replace(/\\/g, "/").replace(/\/+/g, "/").replace(/\/$/, "");
}

/** Backs the plugin-fs mocks with the SUT's in-memory disk (`vfsData`). */
function installDiskMocks(vfsData: SUT["vfsData"]): void {
  vi.mocked(tauriFs.readDir).mockImplementation(async (p) => {
    const prefix = `${normalizePath(p.toString())}/`;
    return Array.from(vfsData.entries())
      .filter(([path]) => path.startsWith(prefix) && !path.slice(prefix.length).includes("/"))
      .map(([path, node]) => ({
        name: path.slice(prefix.length),
        isDirectory: node.kind === "directory",
        isFile: node.kind === "file",
        isSymlink: false,
      })) as any;
  });
  vi.mocked(tauriFs.mkdir).mockImplementation(async (p) => {
    vfsData.set(normalizePath(p.toString()), { kind: "directory" });
  });
  vi.mocked(tauriFs.writeFile).mockImplementation(async (p, data) => {
    const decoded = new TextDecoder().decode(data as Uint8Array);
    vfsData.set(normalizePath(p.toString()), { kind: "file", content: decoded });
  });
  vi.mocked(tauriFs.readTextFile).mockImplementation(async (p) => {
    return vfsData.get(normalizePath(p.toString()))?.content ?? "";
  });
}

/** Walks `relativePath` one entry at a time, as the File System Access API requires. */
async function getFileHandleAt(
  root: EffectDirectoryHandle,
  relativePath: string,
  options?: { create?: boolean },
) {
  const parts = relativePath.split("/").filter(Boolean);
  const fileName = parts.pop()!;
  let dir = root;
  for (const part of parts) dir = await dir.getDirectoryHandle(part, options);
  return dir.getFileHandle(fileName, options);
}

/**
 * Command: Create or Write file into directory
 */
class WriteFileCommand implements fc.AsyncCommand<FsModel, SUT> {
  constructor(
    readonly relativePath: string,
    readonly content: string,
  ) {}

  check(): boolean {
    return true;
  }

  async run(model: FsModel, sut: SUT): Promise<void> {
    const parts = this.relativePath.split("/").filter(Boolean);
    const fileName = parts.pop()!;
    const fullPath = `root/${this.relativePath}`;

    // Update Model
    let currentDir = model.root;
    for (const part of parts) {
      if (!currentDir.children!.has(part)) {
        currentDir.children!.set(part, {
          kind: "directory",
          name: part,
          children: new Map(),
        });
      }
      currentDir = currentDir.children!.get(part)!;
    }
    currentDir.children!.set(fileName, {
      kind: "file",
      name: fileName,
      content: this.content,
    });

    // Execute SUT
    const fileHandle = await getFileHandleAt(sut.rootHandle, this.relativePath, { create: true });
    const writable = await fileHandle.createWritable();
    const writer = writable.getWriter();
    await writer.write(new TextEncoder().encode(this.content));
    await writer.close();

    // Verify written content in SUT matches Model
    const written = sut.vfsData.get(normalizePath(fullPath));
    expect(written).toBeDefined();
    expect(written?.content).toBe(this.content);
  }

  toString(): string {
    return `WriteFile(${this.relativePath}, len=${this.content.length})`;
  }
}

/**
 * Command: Read file and assert consistency
 */
class ReadFileCommand implements fc.AsyncCommand<FsModel, SUT> {
  constructor(readonly relativePath: string) {}

  check(model: Readonly<FsModel>): boolean {
    const parts = this.relativePath.split("/").filter(Boolean);
    let curr = model.root;
    for (const part of parts) {
      if (!curr.children || !curr.children.has(part)) return false;
      curr = curr.children.get(part)!;
    }
    return curr.kind === "file";
  }

  async run(model: FsModel, sut: SUT): Promise<void> {
    const parts = this.relativePath.split("/").filter(Boolean);
    let curr = model.root;
    for (const part of parts) {
      curr = curr.children!.get(part)!;
    }

    const expectedContent = curr.content ?? "";
    const fullPath = `root/${this.relativePath}`;

    const fileHandle = await getFileHandleAt(sut.rootHandle, this.relativePath);
    const file = await fileHandle.getFile();

    expect(file.name).toBe(parts[parts.length - 1]);
    expect(normalizePath((file as any).path)).toBe(normalizePath(fullPath));
    expect(await file.text()).toBe(expectedContent);
  }

  toString(): string {
    return `ReadFile(${this.relativePath})`;
  }
}

/**
 * Command: List directory entries and assert against Model
 */
class ListDirCommand implements fc.AsyncCommand<FsModel, SUT> {
  check(): boolean {
    return true;
  }

  async run(model: FsModel, sut: SUT): Promise<void> {
    const actualNames: string[] = [];
    for await (const entry of sut.rootHandle.values()) {
      actualNames.push(entry.name);
    }

    const expectedNames = Array.from(model.root.children!.keys());
    expect(actualNames.sort()).toEqual(expectedNames.sort());
  }

  toString(): string {
    return `ListDir()`;
  }
}

describe("FileSystem - Model-Based Testing", () => {
  it("conforms to reference VFS state machine across arbitrary operations", async () => {
    const validSegments = ["a.txt", "b.json", "sub/c.txt", "sub/d.xml", "data/cfg.toml"];

    const commandsArb = fc.commands(
      [
        fc
          .tuple(fc.constantFrom(...validSegments), fc.string())
          .map(([p, content]) => new WriteFileCommand(p, content)),
        fc
          .constantFrom(...validSegments)
          .map((p) => new ReadFileCommand(p)),
        fc.constant(new ListDirCommand()),
      ],
      { maxCommands: 25 },
    );

    await fc.assert(
      fc.asyncProperty(commandsArb, async (cmds) => {
        const model: FsModel = {
          root: { kind: "directory", name: "root", children: new Map() },
        };

        const sut: SUT = {
          rootHandle: new EffectDirectoryHandle("root", "root"),
          vfsData: new Map([["root", { kind: "directory" }]]),
        };
        installDiskMocks(sut.vfsData);

        await fc.asyncModelRun(() => ({ model, real: sut }), cmds);
      }),
      { numRuns: 50 },
    );
  });
});
