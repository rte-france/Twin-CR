/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { getFileContent, getFileInfo, getTemplateDetails, renameTemplate } from "@/services/session-manager";
import { For, Show, createEffect, createResource, createSignal } from "solid-js";
import { CreateSessionModal } from "./CreateSessionModal";
import { TemplateTitle } from "./TemplateTitle";
import { ErrorPanel, errorMessage } from "./ErrorPanel";
import { Icon } from "@iconify-icon/solid";
import { save } from "@tauri-apps/plugin-dialog";
import { writeFile } from "@tauri-apps/plugin-fs";

type TemplateDetailsViewProps = {
  templateId: number;
  templateParentNodeId: number;
  refreshFolder: (nodeId: number) => Promise<void>;
};

type FileItem = {
  name: string;
  storageKey: string;
  content: string;
  isText: boolean;
  role: string;
  loaded?: boolean;
  /** Refused for preview on size */
  tooLarge?: boolean;
  error?: string;
};

export function TemplateDetailsView(props: TemplateDetailsViewProps) {
  const MAX_PREVIEW_SIZE = 5 * 1024 * 1024; // 5 Mo
  const [openedFile, setOpenedFile] = createSignal<string | null>(null);
  const [files, setFiles] = createSignal<FileItem[]>([]);
  const [sessionName, setSessionName] = createSignal<string>("");
  const [dslFile, setDSLFile] = createSignal<string>("");
  const [configPath, setConfigPath] = createSignal("");
  const [showCreateModal, setShowCreateModal] = createSignal(false);
  const [downloading, setDownloading] = createSignal<string | null>(null);
  const [downloadError, setDownloadError] = createSignal<string | null>(null);

  const [templateDetails, { refetch }] = createResource(
    () => props.templateId,
    getTemplateDetails
  );

  async function handleRenameTemplate(id: number, newName: string) {
    const result = await renameTemplate(id, newName);
    await refetch();
    props.refreshFolder(props.templateParentNodeId);
    return result;
  }

  createEffect(() => {
    const details = templateDetails();
    if (!details) return;
    // Session creation needs these two by name; find them by their role.
    const byRole = (role: string) =>
      details.files.find((f) => f.role === role)?.filename ?? "";
    setDSLFile(byRole("dsl_file"));
    setConfigPath(byRole("config_toml_file"));
    setFiles(
      details.files.map((f) => ({
        name: f.filename,
        storageKey: f.s3_key,
        content: "",
        // Only text is previewed; not binaries.
        isText: !/\.(xz|zst|gz|bz2|zip|tar)$/i.test(f.filename),
        role: f.role,
      })),
    );
  });

  const loadFileContent = async (file: FileItem) => {
    if (!file.isText) {
      return;
    }
    if (file.loaded) {
      return;
    }

    const fail = (err: unknown) => {
      console.error(err);
      setFiles((previous) =>
        previous.map((f) =>
          f.storageKey === file.storageKey
            ? { ...f, loaded: true, error: errorMessage(err) }
            : f,
        ),
      );
    };

    let info;
    try {
      info = await getFileInfo(file.storageKey);
    } catch (err) {
      fail(err);
      return;
    }

    if (info.size > MAX_PREVIEW_SIZE) {
      setFiles((previous) =>
        previous.map((f) =>
          f.storageKey === file.storageKey
            ? {
                ...f,
                tooLarge: true,
                loaded: true,
              }
            : f,
        ),
      );
      return;
    }

    try {
      const content = await (await getFileContent(file.storageKey)).text();
      setFiles((previous) =>
        previous.map((f) =>
          f.storageKey === file.storageKey
            ? {
                ...f,
                content,
                loaded: true,
              }
            : f,
        ),
      );
    } catch (err) {
      fail(err);
    }
  };

  const downloadFile = async (file: FileItem) => {
    setDownloadError(null);
    // Template paths keep their directories; only the base name is a sensible default.
    const path = await save({ defaultPath: file.name.split("/").pop() });
    if (!path) return;

    setDownloading(file.storageKey);
    try {
      const response = await getFileContent(file.storageKey);
      await writeFile(path, new Uint8Array(await response.arrayBuffer()));
    } catch (err) {
      console.error(err);
      setDownloadError(`Could not download ${file.name}: ${errorMessage(err)}`);
    } finally {
      setDownloading(null);
    }
  };

  const toggleFile = async (file: FileItem) => {
    if (openedFile() === file.name) {
      setOpenedFile(null);
      return;
    }

    setOpenedFile(file.name);
    await loadFileContent(file);
  };

  return (
    <div class="flex h-full w-full gap-4 p-2 overflow-hidden">
      {/* LEFT PANEL */}
      <div class="w-1/5">
        <div class="bg-white border border-slate-300 overflow-hidden">
          <div class="px-4 py-3 bg-slate-900 border-b border-cyan-600">
            <div class="flex items-center font-mono text-xs font-bold uppercase tracking-[0.25em] text-slate-300">
              <Icon class="mr-2" icon="lucide:file-text" />
              Template
            </div>
          </div>

          <div class="p-4">
            <TemplateTitle name={templateDetails()?.name ??""} templateId={props.templateId} onRename={(id, newName) => handleRenameTemplate(id, newName)}/>

            <div class="mt-4 space-y-3 text-xs">
              <div>
                <div class="font-mono uppercase tracking-wide text-slate-500">
                  Owner
                </div>
                <div class="text-slate-800">
                  {templateDetails()?.owner}
                </div>
              </div>

              <div>
                <div class="font-mono uppercase tracking-wide text-slate-500">
                  Shares
                </div>
                <div class="text-slate-800">
                  ...
                </div>
              </div>
            </div>
          </div>
        </div>

        <button
          class="mt-3 w-full px-4 py-2 bg-slate-800 hover:bg-cyan-600 text-white font-mono text-xs font-bold uppercase tracking-wider transition-colors"
          onClick={() => setShowCreateModal(true)}
        >
          Create Session
        </button>
      </div>

      {/* RIGHT PANEL */}
      <div class="w-4/5">
        <div class="h-full bg-white border border-slate-300 flex flex-col">
          <div class="px-4 py-3 bg-slate-900 border-b border-cyan-600">
            <span class="font-mono text-xs font-bold uppercase tracking-[0.25em] text-slate-300">
              Template Assets
            </span>
          </div>

          <ErrorPanel message={downloadError()} class="m-3" />

          <div class="flex-1 min-h-0 overflow-y-auto">
            <For each={files()}>
              {(file) => (
                <div class="border-b border-slate-200 last:border-b-0">
                  <div class="flex items-stretch hover:bg-slate-50 transition-colors">
                    <button
                      class="w-full flex-1 min-w-0 flex justify-between items-center px-4 py-3 text-left"
                      onClick={() => toggleFile(file)}
                    >
                      <span class="flex items-center text-sm">
                        <Icon
                          class="mr-2 text-cyan-600"
                          icon="lucide:file"
                        />
                        {file.name}
                        <span class="ml-2 font-mono text-[10px] uppercase tracking-wider text-slate-400">
                          {file.role}
                        </span>
                      </span>

                      <Icon
                        icon={
                          openedFile() === file.name
                            ? "lucide:chevron-down"
                            : "lucide:chevron-right"
                        }
                      />
                    </button>
                    <button
                      class="px-3 text-slate-500 hover:text-cyan-600 disabled:opacity-50 transition-colors"
                      title={`Download ${file.name}`}
                      disabled={downloading() !== null}
                      onClick={() => downloadFile(file)}
                    >
                      <Icon
                        class={downloading() === file.storageKey ? "animate-spin" : ""}
                        icon={
                          downloading() === file.storageKey
                            ? "lucide:loader"
                            : "lucide:download"
                        }
                      />
                    </button>
                  </div>

                  <Show when={openedFile() === file.name}>
                    <div class="bg-slate-50 border-t border-slate-200">
                      <Show
                        when={file.loaded}
                        fallback={
                          <div class="p-6 flex justify-center text-slate-500">
                            <Show
                              when={file.isText}
                              fallback={"Binary file (preview unavailable)"}
                            >
                              <div class="flex items-center font-mono text-xs">
                                <Icon
                                  class="mr-2 animate-spin"
                                  icon="lucide:loader"
                                />
                                Loading ...
                              </div>
                            </Show>
                          </div>
                        }
                      >
                        <Show
                          when={!file.error}
                          fallback={
                            <ErrorPanel message={file.error ?? null} class="m-3" />
                          }
                        >
                          <textarea
                            readonly
                            class={`w-full font-mono text-xs bg-slate-950 text-slate-200 border-0 resize-none
                              ${
                                file.tooLarge
                                  ? "h-12 text-center pt-3 text-slate-400"
                                  : "h-96 p-4"
                              }
                            `}
                            value={
                              file.tooLarge ? "File too large to display" : file.content
                            }
                          />
                        </Show>
                      </Show>
                    </div>
                  </Show>
                </div>
              )}
            </For>
          </div>
        </div>
      </div>

      {/* CREATE SESSION MODAL */}
      <CreateSessionModal
        open={showCreateModal()}
        sessionName={sessionName()}
        dslFile={dslFile()}
        configPath={configPath()}
        templateId={props.templateId}
        onSessionNameChange={setSessionName}
        onDslFileChange={setDSLFile}
        onConfigPathChange={setConfigPath}
        onClose={() => setShowCreateModal(false)}
      />

    </div>
  );
}
