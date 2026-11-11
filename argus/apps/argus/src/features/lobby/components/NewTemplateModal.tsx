/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createSignal, For, onMount, Show, onCleanup } from "solid-js";
import {
  createTemplate,
  createTemplateExpert,
  dynawoDependencies,
  getTemplateFolders,
} from "@/services/session-manager/service";
import { parse } from "smol-toml";
import { TemplateFolder } from "@/services/session-manager/types";
import { Icon } from "@iconify-icon/solid";

type NewTemplateModalProps = {
  onClose: () => void;
  refreshFolder: (nodeId: number) => Promise<void>;
  parentNodeId: number | null;
};

/**
 * `reference` as written in `fromFile` (relative to that file's directory),
 * as a normalized "/"-separated path relative to the template root.
 * References (e.g. a Dynawo .jobs file) may use "..", but must stay inside the template root.
 */
function resolveReference(fromFile: string, reference: string): string {
  const baseDir = fromFile.includes("/")
    ? fromFile.slice(0, fromFile.lastIndexOf("/") + 1)
    : "";
  const parts: string[] = [];
  for (const part of (baseDir + reference).split(/[\\/]/)) {
    if (!part || part === ".") continue;
    if (part === "..") {
      if (parts.length === 0) {
        throw new Error(
          `${reference} (referenced by ${fromFile}) points outside the template folder`,
        );
      }
      parts.pop();
    } else {
      parts.push(part);
    }
  }
  return parts.join("/");
}

/** The directory at `relativePath` (as returned by resolveReference) under `root`. */
async function getDirectoryHandleAt(
  root: FileSystemDirectoryHandle,
  relativePath: string,
): Promise<FileSystemDirectoryHandle> {
  let dir = root;
  for (const part of relativePath.split("/").filter(Boolean)) {
    dir = await dir.getDirectoryHandle(part);
  }
  return dir;
}

/** The file at `relativePath` (as returned by resolveReference) under `root`. */
async function getFileHandleAt(
  root: FileSystemDirectoryHandle,
  relativePath: string,
): Promise<FileSystemFileHandle> {
  const slash = relativePath.lastIndexOf("/");
  const dir = await getDirectoryHandleAt(root, relativePath.slice(0, slash + 1));
  return dir.getFileHandle(relativePath.slice(slash + 1));
}

export function NewTemplateModal(props: NewTemplateModalProps) {
  const [dslFile, setDslFile] = createSignal<File>();
  const [configFile, setConfigFile] = createSignal<File>();
  const [configPath, setConfigPath] = createSignal<string>("");
  const [templateName, setTemplateName] = createSignal("");
  const [parentNodeId, setParentNodeId] = createSignal<number>();
  const [templateFolders, setTemplateFolders] =
    createSignal<TemplateFolder[]>();
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal<string | null>(null);
  const [mode, setMode] = createSignal<"guided" | "expert">("guided");
  const [progress, setProgress] = createSignal("");
  const [jobFile, setJobFile] = createSignal<File>();
  const [jobPath, setJobPath] = createSignal<string>("");
  const [cyberConfigFile, setCyberConfigFile] = createSignal<File>();
  const [assetSimulatorConfigFile, setAssetSimulatorConfigFile] = createSignal<File>();
  const [extraIoFile, setExtraIoFile] = createSignal<File>();
  const [otherFiles, setOtherFiles] = createSignal<File[]>([]);
  const [automataCommands, setAutomataCommands] = createSignal("");
  const [geoDataFile, setGeoDataFile] = createSignal<File>();
  const [scenarioFile, setScenarioFile] = createSignal<File>();
  const [mappingFile, setMappingFile] = createSignal<File>();
  const [scadaIidmFile, setScadaIidmFile] = createSignal<File>();
  const [gmIidmFile, setGmIidmFile] = createSignal<File>();
  const [period, setPeriod] = createSignal(1);
  const [dynawoVariant, setDynawoVariant] = createSignal<"public" | "rte">(
    "rte",
  );

  const isSubmitDisabled = () => loading() || !canCreate();

  onMount(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        props.onClose();
      }
      if (e.key === "Enter" && !isSubmitDisabled()) {
        handleCreateClick();
      }
    };
    window.addEventListener("keydown", handler);
    onCleanup(() => window.removeEventListener("keydown", handler));

    void (async () => {
      const templateFolders = await getTemplateFolders();
      setTemplateFolders(templateFolders);
      if (templateFolders.length > 0) {
        setParentNodeId(templateFolders[0].node_id);
      }
    })();
  });

  const parentId = () =>
      props.parentNodeId == null ? parentNodeId() : props.parentNodeId;

  const handleCreateClick = async () => {
    try {
      if (mode() === "expert") {
        await handleExpertSubmit();
      } else {
        await handleSubmit();
      }
      const parent = parentId();
      if (parent !== undefined) await props.refreshFolder(parent);
      props.onClose();
    }
    catch (err) {
      // Keep the modal open: closing here would look like success.
      console.error(err);
      setError(err instanceof Error ? err.message : String(err));
    }
    finally {
      setLoading(false);
      setProgress("");
    }
  };

  /** File picker that keeps both the File and its absolute path. */
  async function pickFile(
    label: string,
    extensions: string[],
    setFile: (f: File) => void,
    setPath?: (p: string) => void,
  ) {
    try {
      const [handle] = await window.showOpenFilePicker({
        types: [
          {
            description: label,
            accept: { "*/*": extensions.map((e) => `.${e}`) },
          },
        ],
      });
      if (!handle) return;
      const file = await handle.getFile();
      setFile(file);
      const filePath = (file as any).path || "";
      setPath?.(filePath);
    } catch (err: any) {
      if (err?.name === "AbortError") return;
      throw err;
    }
  }

  /** Multiple file picker, any extension: the picked files are added to `current`. */
  async function pickFiles(current: File[], setFiles: (f: File[]) => void) {
    try {
      // No `types`: an entry without `accept` would become an empty dialog filter.
      const handles = await window.showOpenFilePicker({ multiple: true });
      const picked = await Promise.all(handles.map((handle) => handle.getFile()));
      const names = new Set(picked.map((f) => f.name));
      setFiles([...current.filter((f) => !names.has(f.name)), ...picked]);
    } catch (err: any) {
      if (err?.name === "AbortError") return;
      throw err;
    }
  }

  /**
   * Guided uploads are driven by the jobs file: everything it references is
   * resolved through the server so the Dynawo convention is not duplicated
   * here, and the connectors file is skipped because the server generates it.
   */
  async function collectJobsClosure(
    jobFile: File,
    jobPath: string,
  ): Promise<{ relativePath: string; file: File }[]> {
    const lastSlash = Math.max(jobPath.lastIndexOf("/"), jobPath.lastIndexOf("\\"));
    const jobDir = lastSlash >= 0 ? jobPath.slice(0, lastSlash) : "";
    const jobBase = lastSlash >= 0 ? jobPath.slice(lastSlash + 1) : jobPath;
    const dirHandle = await window.showDirectoryPicker({ startIn: jobDir });

    const queue: string[] = [jobBase];
    const walked = new Set<string>();
    const needed = new Set<string>();

    while (queue.length > 0) {
      const current = queue.pop()!;
      if (walked.has(current)) continue;
      walked.add(current);

      setProgress(`Resolving ${current}...`);
      const fileHandle = await getFileHandleAt(dirHandle, current);
      const xml = current === jobBase ? jobFile : await fileHandle.getFile();
      for (const reference of await dynawoDependencies(xml)) {
        if (reference.startsWith("RTConnectors")) continue;
        const relativePath = resolveReference(current, reference);
        needed.add(relativePath);
        if (relativePath.endsWith(".dyd")) queue.push(relativePath);
      }
    }

    const collected: { relativePath: string; file: File }[] = [];
    for (const relativePath of needed) {
      setProgress(`Reading ${relativePath}...`);
      const fileHandle = await getFileHandleAt(dirHandle, relativePath);
      collected.push({
        relativePath,
        file: await fileHandle.getFile(),
      });
    }
    return collected;
  }

  /**
   * Collect an existing context the way upload_context.py does: everything the
   * config.toml names, its other_files, and the transitive closure of the jobs
   * file. The jobs/dyd convention is resolved server-side so it is not
   * duplicated here.
   */
  async function collectExpertFiles(
    configFile: File,
    configPath: string,
  ): Promise<{ relativePath: string; file: File }[]> {
    const lastSlash = Math.max(configPath.lastIndexOf("/"), configPath.lastIndexOf("\\"));
    const configDir = lastSlash >= 0 ? configPath.slice(0, lastSlash) : "";
    const dirHandle = await window.showDirectoryPicker({ startIn: configDir });

    const config = parse(await configFile.text()) as Record<string, any>;
    const inputFiles = config.input_files;
    if (!inputFiles) {
      throw new Error(`${configFile.name} has no [input_files] section`);
    }

    // Paths in config.toml are relative to its own directory, the template root.
    const fromConfig = (path: string) => resolveReference(configFile.name, path);
    const wanted = new Set<string>();
    const wantedDirs = new Set<string>();
    const collectSection = (section: Record<string, any>) => {
      for (const [key, value] of Object.entries(section)) {
        if (key === "other_files" || key === "other_dirs") continue;
        if (typeof value === "string") wanted.add(fromConfig(value));
      }
      for (const other of section.other_files ?? []) wanted.add(fromConfig(other));
      for (const dir of section.other_dirs ?? []) wantedDirs.add(fromConfig(dir));
    };
    collectSection(inputFiles);
    for (const [key, value] of Object.entries(inputFiles)) {
      if (key === "other_files" || key === "other_dirs") continue;
      // Recursively check tables like input_files.scada_backend, etc.
      if (value && typeof value === "object" && !Array.isArray(value)) {
        collectSection(value);
      }
    }

    for (const dir of wantedDirs) {
      setProgress(`Listing ${dir}...`);
      const subDirHandle = await getDirectoryHandleAt(dirHandle, dir);
      for await (const item of listFilesRecursive(subDirHandle, dir)) {
        wanted.add(item.relativePath);
      }
    }

    if (!inputFiles.job_file) throw new Error(`${configFile.name} declares no job_file`);
    const jobFile = fromConfig(inputFiles.job_file);

    // Walk the jobs graph: the server names what each XML file references,
    // relative to the referencing file's own directory.
    const queue: string[] = [jobFile];
    const walked = new Set<string>();
    while (queue.length > 0) {
      const current = queue.pop()!;
      if (walked.has(current)) continue;
      walked.add(current);
      wanted.add(current);

      setProgress(`Resolving ${current}...`);
      const fileHandle = await getFileHandleAt(dirHandle, current);
      const xml = await fileHandle.getFile();
      for (const reference of await dynawoDependencies(xml)) {
        const relativePath = resolveReference(current, reference);
        wanted.add(relativePath);
        if (relativePath.endsWith(".dyd")) queue.push(relativePath);
      }
    }

    const collected: { relativePath: string; file: File }[] = [];
    for (const relativePath of wanted) {
      setProgress(`Reading ${relativePath}...`);
      const fileHandle = await getFileHandleAt(dirHandle, relativePath);
      collected.push({
        relativePath,
        file: await fileHandle.getFile(),
      });
    }
    return collected;
  }

  /** Every file under `dir` (relative to `root`), as "/"-separated paths relative to `root`. */
  async function* listFilesRecursive(
    dirHandle: FileSystemDirectoryHandle,
    basePath = "",
  ): AsyncGenerator<{ relativePath: string; file: File }> {
    for await (const entry of dirHandle.values()) {
      const relativePath = basePath ? `${basePath}/${entry.name}` : entry.name;

      if (entry.kind === "file") {
        yield {
          relativePath,
          file: await entry.getFile(),
        };
      } else if (entry.kind === "directory") {
        yield* listFilesRecursive(entry, relativePath);
      }
    }
  }

  const handleExpertSubmit = async () => {
    const parent = parentId();
    const config = configFile();
    if (parent === undefined) throw new Error("parentId not defined");
    if (!config) throw new Error("Select a config.toml first");

    setError(null);
    setLoading(true);
    try {
      const files = await collectExpertFiles(config, configPath());
      setProgress(`Uploading ${files.length} files...`);
      await createTemplateExpert(templateName(), parent, config, files);
    } catch (err) {
      throw err;
    }
  };

  /**
   * A mapping file is required when a cyber config file is specified.
   */
  const mappingMissing = () =>
    mode() === "guided" &&
    cyberConfigFile() !== undefined &&
    mappingFile() === undefined;

  /** Whether every field the chosen mode requires has a value. */
  const canCreate = () =>
    templateName().trim().length > 0 &&
    parentId() !== undefined &&
    !mappingMissing() &&
    (mode() === "guided"
      ? jobFile() !== undefined
      : configFile() !== undefined);

  const handleSubmit = async () => {
    const parent = parentId();
    if (parent === undefined) throw new Error("parentId not defined");

    const job = jobFile();
    if (!job) throw new Error("Select a jobs file");

    setError(null);
    setLoading(true);
    try {
      const dynawoFiles = await collectJobsClosure(job, jobPath());

      const optional: Record<string, File> = {};
      for (const [field, signal] of [
        ["dsl_file", dslFile],
        ["cyber_config_file", cyberConfigFile],
        ["asset_simulator_config_file", assetSimulatorConfigFile],
        ["extra_io_file", extraIoFile],
        ["geo_data", geoDataFile],
        ["scenario_file", scenarioFile],
        ["mapping_file", mappingFile],
        ["scada_iidm_file", scadaIidmFile],
        ["gm_iidm_file", gmIidmFile],
      ] as const) {
        const file = signal();
        if (file) optional[field] = file;
      }

      // One request covers both, and the generation is the slow half.
      setProgress(
        `Uploading ${dynawoFiles.length + 1} files, then generating outputs (this can take a while)...`,
      );
      await createTemplate(
        templateName(), parent, job, dynawoFiles, optional, period(),
        dynawoVariant(), otherFiles(),
        automataCommands().split("\n").map((c) => c.trim()).filter((c) => c.length > 0),
      );
    } catch (err) {
      throw err;
    }
  };

  return (
    <>
      <div class="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
        <div class="bg-white p-6 w-full max-w-4xl shadow-xl">
          <h2 class="text-xl font-semibold mb-1">Create new template</h2>

          <div class="mb-4 flex border-b border-gray-200 text-sm">
            <button
              type="button"
              disabled={loading()}
              onClick={() => {
                setMode("guided");
                setError(null);
              }}
              class={`px-3 py-2 -mb-px border-b-2 ${
                mode() === "guided"
                  ? "border-cyan-600 font-medium text-slate-900"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Guided
            </button>
            <button
              type="button"
              disabled={loading()}
              onClick={() => {
                setMode("expert");
                setError(null);
              }}
              class={`px-3 py-2 -mb-px border-b-2 ${
                mode() === "expert"
                  ? "border-cyan-600 font-medium text-slate-900"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              Expert
            </button>
          </div>

          <p class="mb-3 text-xs text-gray-500">
            <Show
              when={mode() === "guided"}
              fallback={
                "Uploads an existing context as-is, no files are auto-generated."
              }
            >
              Uploads a minimal set of inputs and generates the rest.
            </Show>
          </p>

          <div
            class={
              mode() === "guided"
                ? "grid grid-cols-2 gap-6 items-start"
                : "flex flex-col gap-2"
            }
          >
            {/* Main column */}
            <div class="flex flex-col gap-2">
              <label class="text-xs text-gray-500">Template name</label>
              <input
                class="border border-gray-300 rounded px-2 py-1"
                value={templateName()}
                onInput={(e) => setTemplateName(e.currentTarget.value)}
              />

              <Show when={props.parentNodeId == null}>
                <>
                  <label class="text-xs text-gray-500">Parent folder</label>
                  <select
                    class="border border-gray-300 rounded px-2 py-1"
                    value={parentNodeId() ?? ""}
                    onChange={(e) => {
                      setParentNodeId(Number(e.currentTarget.value));
                    }}
                  >
                    <For each={templateFolders()}>
                      {(folder) => (
                        <option value={folder.node_id}>
                          {folder.path}
                        </option>
                      )}
                    </For>
                  </select>
                </>
              </Show>

              <Show when={mode() === "guided"}>
                <>
                  <label class="text-xs text-gray-500">
                    Jobs file (required)
                  </label>

                  <div class="flex gap-1">
                    <button
                      type="button"
                      class="flex-1 border border-gray-300 rounded px-2 py-1 text-left"
                      onClick={() =>
                        pickFile(
                          "Dynawo jobs",
                          ["jobs"],
                          setJobFile,
                          setJobPath,
                        )}
                    >
                      {jobFile()?.name ?? "Select .jobs"}
                    </button>

                    <Show when={jobFile()}>
                      <button
                        type="button"
                        class="border border-gray-300 rounded px-2 py-1 text-xs text-gray-500 hover:text-red-600"
                        onClick={() => {
                          setJobFile(undefined);
                          setJobPath("");
                        }}
                        title="Clear selection"
                      >
                        ✕
                      </button>
                    </Show>
                  </div>

                  <label class="text-xs text-gray-500">
                    Dynawo build
                  </label>
                  <select
                    class="border border-gray-300 rounded px-2 py-1"
                    value={dynawoVariant()}
                    onChange={(e) =>
                      setDynawoVariant(
                        e.currentTarget.value as "public" | "rte",
                      )}
                  >
                    <option value="public">Public</option>
                    <option value="rte">RTE</option>
                  </select>

                  <label class="text-xs text-gray-500">
                    Master period (s)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    class="border border-gray-300 rounded px-2 py-1"
                    value={period()}
                    onInput={(e) =>
                      setPeriod(Number(e.currentTarget.value))}
                  />
                </>
              </Show>

              <Show when={mode() === "expert"}>
                <>
                  <label class="text-xs text-gray-500">
                    Config toml file
                  </label>

                  <div class="flex gap-1">
                    <button
                      type="button"
                      class="flex-1 border border-gray-300 rounded px-2 py-1 text-left"
                      onClick={() =>
                        pickFile(
                          "Config",
                          ["toml"],
                          setConfigFile,
                          setConfigPath,
                        )}
                    >
                      {configFile()?.name ?? "Select config.toml"}
                    </button>

                    <Show when={configFile()}>
                      <button
                        type="button"
                        class="border border-gray-300 rounded px-2 py-1 text-xs text-gray-500 hover:text-red-600"
                        onClick={() => {
                          setConfigFile(undefined);
                          setConfigPath("");
                        }}
                        title="Clear selection"
                      >
                        ✕
                      </button>
                    </Show>
                  </div>
                </>
              </Show>
            </div>

            {/* Optional column */}
            <Show when={mode() === "guided"}>
              <div class="flex flex-col gap-2">
                <p class="text-xs font-medium text-gray-600">
                  Optional
                </p>

                <For
                  each={[
                    {
                      label: "DSL file",
                      hint: "DSL scenario file",
                      exts: ["dsl"],
                      get: dslFile,
                      set: setDslFile,
                    },
                    {
                      label: "Cyber network",
                      hint:
                        "IFL model of the cyber network. Requires a cyber mapping.",
                      exts: ["json"],
                      get: cyberConfigFile,
                      set: setCyberConfigFile,
                    },
                    {
                      label: "Cyber mapping",
                      hint:
                        "Mapping of the telesignals (TS, TM, TC, TVC).",
                      exts: ["xz", "json"],
                      get: mappingFile,
                      set: setMappingFile,
                    },
                    {
                      label: "SCADA grid model",
                      hint:
                        "Grid model for the SCADA backend, when it differs from the one the simulation runs on. Also read for the current limits, so XIIDM (the arc is not supported).",
                      exts: ["zst", "xz", "xiidm", "iidm", "xml"],
                      get: scadaIidmFile,
                      set: setScadaIidmFile,
                    },
                    {
                        label: "GM grid model",
                        hint: "Grid model for the game master backend, when it differs from the one the simulation runs on",
                        exts: ["zst", "xz", "xiidm", "iidm", "xml"],
                        get: gmIidmFile,
                        set: setGmIidmFile,
                    },
                    {
                      label: "Asset simulator config",
                      hint:
                        "Asset simulator configuration, for models not included in Dynawo. Generated from the cyber network and its mapping when left out.",
                      exts: ["json"],
                      get: assetSimulatorConfigFile,
                      set: setAssetSimulatorConfigFile,
                    },
                    {
                      label: "Extra IO",
                      hint:
                        "Entries added to the generated game master and SCADA inputs/outputs, e.g. a SCADA input read by a python automaton.",
                      exts: ["json"],
                      get: extraIoFile,
                      set: setExtraIoFile,
                    },
                    {
                      label: "Geo data",
                      hint:
                        "Geographical position of substations",
                      exts: ["json"],
                      get: geoDataFile,
                      set: setGeoDataFile,
                    },
                    {
                      label: "Scenario",
                      hint: "Legacy scenario file",
                      exts: ["json"],
                      get: scenarioFile,
                      set: setScenarioFile,
                    },
                  ]}
                >
                  {(field) => (
                    <div class="flex flex-col">
                      <div class="flex gap-1">
                        <button
                          type="button"
                          class="flex-1 border border-gray-300 rounded px-2 py-1 text-left text-xs"
                          onClick={() =>
                            pickFile(
                              field.label,
                              field.exts,
                              field.set,
                            )}
                        >
                          {field.get()?.name ??
                            `Select ${field.label.toLowerCase()}`}
                        </button>

                        <Show when={field.get()}>
                          <button
                            type="button"
                            class="border border-gray-300 rounded px-2 py-1 text-xs text-gray-500 hover:text-red-600"
                            onClick={() => field.set(undefined)}
                            title="Clear selection"
                          >
                            ✕
                          </button>
                        </Show>
                      </div>

                      <span class="mt-0.5 text-[11px] leading-snug text-gray-400">
                        {field.hint}
                      </span>
                    </div>
                  )}
                </For>

                <div class="flex flex-col">
                  <button
                    type="button"
                    class="border border-gray-300 rounded px-2 py-1 text-left text-xs"
                    onClick={() => pickFiles(otherFiles(), setOtherFiles)}
                  >
                    Add other files
                  </button>
                  <For each={otherFiles()}>
                    {(file) => (
                      <div class="flex items-center justify-between text-xs px-2">
                        <span class="truncate">{file.name}</span>
                        <button
                          type="button"
                          class="text-gray-400 hover:text-red-500"
                          title={`Remove ${file.name}`}
                          onClick={() => setOtherFiles(otherFiles().filter((f) => f !== file))}
                        >
                          ✕
                        </button>
                      </div>
                    )}
                  </For>
                  <span class="mt-0.5 text-[11px] leading-snug text-gray-400">
                    Files used at runtime but not generated, e.g. a python automaton (config.toml other_files).
                  </span>
                </div>

                <label class="text-xs text-gray-500">Automata commands</label>
                <textarea
                  class="border border-gray-300 rounded px-2 py-1 text-xs font-mono"
                  rows={2}
                  placeholder="python tcp_blocker.py"
                  value={automataCommands()}
                  onInput={(e) => setAutomataCommands(e.currentTarget.value)}
                />
                <span class="-mt-1 text-[11px] leading-snug text-gray-400">
                  One command per line, run from the template folder to launch the automata (config.toml automata_commands).
                </span>
              </div>
            </Show>
          </div>

          <Show when={progress()}>
            {(text) => (
              <p class="mt-4 font-mono text-xs text-slate-500">{text()}</p>
            )}
          </Show>

          <Show when={mappingMissing()}>
            <p class="mt-4 border-l-2 border-amber-600 bg-amber-50 px-3 py-2 text-xs text-amber-900">
              A cyber network needs a cyber mapping.
            </p>
          </Show>

          <Show when={error()}>
            {(message) => (
              <p class="mt-4 border-l-2 border-red-600 bg-red-50 px-3 py-2 text-xs text-red-800">
                {message()}
              </p>
            )}
          </Show>

          <div class="flex justify-end gap-3 mt-6">
            <button
              class="bg-gray-200 px-3 py-1 text-xs enabled:hover:bg-gray-300 disabled:opacity-50"
              disabled={loading()}
              onClick={() => props.onClose()}
            >
              Cancel
            </button>

            <button
              class="px-3 py-1 bg-slate-800 enabled:hover:bg-cyan-600 text-white font-mono text-xs font-bold uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              disabled={isSubmitDisabled()}
              onClick={() => handleCreateClick()}
            >
              {loading() ? (
                <>
                  <Icon class="mr-1 animate-spin" icon="lucide:loader" />
                  Uploading
                </>
              ) : (
                "Create"
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
