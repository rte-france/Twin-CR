/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { Context, Effect } from "effect";
import { createSignal, createMemo } from "solid-js";
import { LobbyService } from "@/features/workspace/services/lobby";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import {
  defaultContentFor,
  isEditableFile,
  looksLikeStub,
} from "../utils/constants";
import type {
  FileNode,
  FlatMap,
  SelectedArtifactsMap,
  PreparedSession,
  FileNodeInfo,
} from "../types";

export function createCoreStore(projectId: string) {
  const [loading, setLoading] = createSignal(false);

  function run<A, E>(effect: Effect.Effect<A, E, LobbyService>): Promise<A> {
    return getSystemRuntime().runPromise(effect);
  }

  function runLobby<A, E>(
    f: (svc: Context.Tag.Service<typeof LobbyService>) => Effect.Effect<A, E>,
  ): Promise<A> {
    return run(LobbyService.pipe(Effect.andThen(f)));
  }

  const errorMessage = (e: unknown) =>
    e instanceof Error || (typeof e === "object" && e && "message" in e)
      ? String((e as { message: unknown }).message)
      : String(e);

  return { projectId, loading, setLoading, runLobby, errorMessage };
}

export function createFileSystemStore(
  core: ReturnType<typeof createCoreStore>,
  callbacks: { onNodeDeleted: (id: string) => void },
) {
  const [fileSystem, setFileSystem] = createSignal<FileNode[]>([]);
  const [flatMap, setFlatMap] = createSignal<FlatMap>({});
  const [currentFolderId, setCurrentFolderId] = createSignal<string | null>(
    null,
  );

  function buildFlatMap(
    nodes: FileNode[],
    parentId: string | null,
    map: FlatMap,
  ) {
    for (const node of nodes) {
      node._parentId = parentId;
      map[node.id] = node;
      if (node.children) buildFlatMap(node.children, node.id, map);
    }
  }

  async function loadFileSystem() {
    try {
      const nodes = (await core.runLobby((svc) =>
        svc.fetchFileSystem(core.projectId),
      )) as FileNode[];
      const map: FlatMap = {};
      buildFlatMap(nodes, null, map);
      setFileSystem(nodes);
      setFlatMap(map);
    } catch (e) {}
  }

  function getAllFileNodes(nodeId: string, basePath = ""): FileNodeInfo[] {
    const node = flatMap()[nodeId];
    if (!node) return [];
    if (!node.is_directory) return [{ file: node, path: basePath }];
    return (node.children || []).flatMap((child) =>
      getAllFileNodes(
        child.id,
        basePath ? `${basePath}/${node.name}` : node.name,
      ),
    );
  }

  async function promptCreateFolder() {
    const name = prompt("Folder name:");
    if (!name) return;
    core.setLoading(true);
    try {
      await core.runLobby((svc) =>
        svc.createDirectory(core.projectId, name, currentFolderId()),
      );
      await loadFileSystem();
    } catch (e) {
      alert(`Error creating folder: ${core.errorMessage(e)}`);
    } finally {
      core.setLoading(false);
    }
  }

  async function renameItem(id: string) {
    const node = flatMap()[id];
    if (!node) return;
    const newName = prompt("Rename to:", node.name);
    if (!newName || newName === node.name) return;
    try {
      await core.runLobby((svc) => svc.renameItem(core.projectId, id, newName));
      await loadFileSystem();
    } catch (e) {
      alert(`Error renaming item: ${core.errorMessage(e)}`);
    }
  }

  async function deleteItem(id: string) {
    const node = flatMap()[id];
    if (!node) return;
    if (!confirm(`Delete "${node.name}" ?`)) return;

    callbacks.onNodeDeleted(id);

    try {
      await core.runLobby((svc) => svc.deleteItem(core.projectId, id));
      await loadFileSystem();
    } catch (e) {
      alert(`Error deleting item: ${core.errorMessage(e)}`);
    }
  }

  async function moveItem(itemId: string, newParentId: string | null | "root") {
    if (itemId === newParentId) return;
    try {
      await core.runLobby((svc) =>
        svc.moveItem(
          core.projectId,
          itemId,
          newParentId === "root" ? null : newParentId,
        ),
      );
      await loadFileSystem();
    } catch (e) {
      alert(`Error moving item: ${core.errorMessage(e)}`);
    }
  }

  function navigateTo(id: string | null) {
    setCurrentFolderId(id);
  }

  return {
    fileSystem,
    flatMap,
    currentFolderId,
    loadFileSystem,
    getAllFileNodes,
    promptCreateFolder,
    renameItem,
    deleteItem,
    moveItem,
    navigateTo,
  };
}

export function createArtifactsStore(
  fs: ReturnType<typeof createFileSystemStore>,
) {
  const [selectedArtifacts, setSelectedArtifacts] =
    createSignal<SelectedArtifactsMap>({});

  function toggleArtifactSelection(
    id: string,
    name: string,
    isDir: boolean,
    checked: boolean,
  ) {
    if (isDir) {
      const filesInfo = fs.getAllFileNodes(id);
      setSelectedArtifacts((prev) => {
        const next = { ...prev };
        filesInfo.forEach((info) => {
          if (checked) {
            next[info.file.id] = {
              id: info.file.id,
              name: info.file.name,
              destination: info.path ? `alloc/${info.path}` : "alloc",
            };
          } else {
            delete next[info.file.id];
          }
        });
        return next;
      });
    } else {
      setSelectedArtifacts((prev) => {
        const next = { ...prev };
        if (checked) {
          next[id] = { id, name, destination: "alloc" };
        } else {
          delete next[id];
        }
        return next;
      });
    }
  }

  function removeSelection(id: string) {
    setSelectedArtifacts((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  function updateArtifactDest(id: string, val: string) {
    setSelectedArtifacts((prev) => {
      const current = prev[id];
      if (!current) return prev;
      return { ...prev, [id]: { ...current, destination: val } };
    });
  }

  return {
    selectedArtifacts,
    toggleArtifactSelection,
    removeSelection,
    updateArtifactDest,
  };
}

export function createEditorStore(
  core: ReturnType<typeof createCoreStore>,
  fs: ReturnType<typeof createFileSystemStore>,
) {
  const [selectedFileId, setSelectedFileId] = createSignal<string | null>(null);
  const [editorContent, setEditorContent] = createSignal("");
  const [editorDisabled, setEditorDisabled] = createSignal(false);

  const selectedFileName = createMemo(() => {
    const id = selectedFileId();
    return id ? (fs.flatMap()[id]?.name ?? null) : null;
  });

  const stubWarningVisible = createMemo(
    () => looksLikeStub(editorContent()) && !editorDisabled(),
  );

  function clearEditor() {
    setSelectedFileId(null);
    setEditorContent("");
    setEditorDisabled(false);
  }

  async function selectFile(id: string) {
    setSelectedFileId(id);
    const name = selectedFileName();

    if (!name || !isEditableFile(name)) {
      setEditorContent("Binary file: Text preview is not available.");
      setEditorDisabled(true);
      return;
    }

    setEditorDisabled(false);
    try {
      const rawBytes = await core.runLobby((svc) =>
        svc.readFileRaw(core.projectId, id),
      );
      const content = new TextDecoder().decode(rawBytes);
      setEditorContent(content);
    } catch (e) {
      setEditorContent("Unable to read this file.");
      setEditorDisabled(true);
    }
  }

  async function saveCurrentFile(): Promise<boolean> {
    const id = selectedFileId();
    if (!id) return false;
    try {
      const bytes = new TextEncoder().encode(editorContent());
      await core.runLobby((svc) => svc.writeFileRaw(core.projectId, id, bytes));
      return true;
    } catch (e) {
      alert(`Error saving file: ${core.errorMessage(e)}`);
      return false;
    }
  }

  return {
    selectedFileId,
    selectedFileName,
    editorContent,
    setEditorContent,
    editorDisabled,
    stubWarningVisible,
    clearEditor,
    selectFile,
    saveCurrentFile,
  };
}

export function createUploaderStore(
  core: ReturnType<typeof createCoreStore>,
  fs: ReturnType<typeof createFileSystemStore>,
) {
  async function getOrCreateDirectoryId(
    name: string,
    parentId: string | null,
  ): Promise<string> {
    console.log(
      `🔎 [API] getOrCreateDirectoryId: Cherche dossier "${name}" (parent: ${parentId})`,
    );
    const existingNodes = Object.values(fs.flatMap());
    const found = existingNodes.find(
      (n) => n.name === name && n.is_directory && n._parentId === parentId,
    );

    if (found) {
      console.log(
        `✅ [API] Dossier "${name}" trouvé en local (ID: ${found.id})`,
      );
      return found.id;
    }

    console.log(`⚠️ [API] Dossier "${name}" introuvable, création via API...`);
    const dir = await core.runLobby((svc) =>
      svc.createDirectory(core.projectId, name, parentId),
    );

    console.log(`✅ [API] Dossier "${name}" créé (ID: ${dir.id})`);
    fs.flatMap()[dir.id] = {
      ...dir,
      _parentId: parentId,
    } as unknown as FileNode;
    return dir.id;
  }

  async function createNewFile() {
    const name = prompt("File name:", "main.hcl");
    if (!name) return;
    if (!isEditableFile(name))
      return alert("This extension is binary. Please upload it.");

    core.setLoading(true);
    try {
      const file = new File([new Blob([defaultContentFor(name)])], name);
      await core.runLobby((svc) =>
        svc.uploadFile(core.projectId, file, name, fs.currentFolderId()),
      );
      await fs.loadFileSystem();
      alert(`Fichier "${name}" créé.`);
    } catch (e) {
      alert(`Error creating file: ${core.errorMessage(e)}`);
    } finally {
      core.setLoading(false);
    }
  }

  async function uploadFiles(filesList: FileList) {
    if (!filesList?.length) return;

    // 💡 On "gèle" la liste dans un tableau statique pour qu'elle survive au target.value = ""
    const files = Array.from(filesList);

    core.setLoading(true);
    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        await core.runLobby((svc) =>
          svc.uploadFile(core.projectId, file, file.name, fs.currentFolderId()),
        );
      }
      await fs.loadFileSystem();
    } catch (e) {
      alert(`Error uploading files: ${core.errorMessage(e)}`);
    } finally {
      core.setLoading(false);
    }
  }

  async function uploadFolderInput(filesList: FileList) {
    if (!filesList?.length) return;
    const files = Array.from(filesList);

    core.setLoading(true);

    // 💡 Cache local dédié à cette session d'upload (clé: "parent_id/nom_dossier", valeur: "id_du_dossier")
    const localDirCache: Record<string, string> = {};

    async function getOrCreateDirectoryId(
      name: string,
      parentId: string | null,
    ): Promise<string> {
      const cacheKey = `${parentId ?? "root"}/${name}`;

      // 1. Vérifier le cache local de l'upload
      if (localDirCache[cacheKey]) {
        return localDirCache[cacheKey];
      }

      // 2. Vérifier si le dossier existe déjà dans le FileSystem global du store
      const existingNodes = Object.values(fs.flatMap());
      const found = existingNodes.find(
        (n) => n.name === name && n.is_directory && n._parentId === parentId,
      );

      if (found) {
        localDirCache[cacheKey] = found.id;
        return found.id;
      }

      // 3. Sinon, on le crée via l'API
      const dir = await core.runLobby((svc) =>
        svc.createDirectory(core.projectId, name, parentId),
      );

      localDirCache[cacheKey] = dir.id;

      // Mettre à jour aussi le flatMap global pour la suite
      fs.flatMap()[dir.id] = {
        ...dir,
        _parentId: parentId,
      } as unknown as FileNode;

      return dir.id;
    }

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i] as File & { webkitRelativePath: string };
        const pathString = file.webkitRelativePath || file.name;
        const pathParts = pathString.split("/");
        const fileName = pathParts.pop();

        let currentParent = fs.currentFolderId();

        for (const part of pathParts) {
          const dirId = await getOrCreateDirectoryId(part, currentParent);
          currentParent = dirId;
        }

        if (fileName) {
          try {
            await core.runLobby((svc) =>
              svc.uploadFile(core.projectId, file, fileName, currentParent),
            );
          } catch (e) {
            console.error(
              `❌ [UploadFolder] Erreur upload fichier ${fileName}`,
              e,
            );
          }
        }
      }
      await fs.loadFileSystem();
    } finally {
      core.setLoading(false);
    }
  }

  async function readAllDirectoryEntries(reader: any): Promise<any[]> {
    console.log("📖 [DragDrop] Lecture des sous-éléments d'un dossier...");
    const entries: any[] = [];
    let readChunk = async () => {
      return new Promise<any[]>((resolve, reject) => {
        reader.readEntries(resolve, reject);
      });
    };

    let chunk = await readChunk();
    while (chunk.length > 0) {
      entries.push(...chunk);
      chunk = await readChunk();
    }
    console.log(
      "📖 [DragDrop] Fin de lecture, trouvés :",
      entries.length,
      "éléments",
    );
    return entries;
  }

  async function uploadEntry(entry: any, parentId: string | null) {
    if (entry.isFile) {
      console.log(
        `📄 [DragDrop] Upload du fichier "${entry.name}" dans parent:`,
        parentId,
      );
      const file = await new Promise<File>((resolve, reject) =>
        entry.file(resolve, reject),
      );
      await core.runLobby((svc) =>
        svc.uploadFile(core.projectId, file, entry.name, parentId),
      );
    } else if (entry.isDirectory) {
      console.log(
        `📁 [DragDrop] Traitement du dossier "${entry.name}" dans parent:`,
        parentId,
      );
      try {
        const dirId = await getOrCreateDirectoryId(entry.name, parentId);
        const reader = entry.createReader();
        const entries = await readAllDirectoryEntries(reader);

        for (const child of entries) {
          await uploadEntry(child, dirId);
        }
      } catch (e) {
        console.error(`❌ [DragDrop] Erreur sur le dossier ${entry.name}`, e);
      }
    }
  }

  async function handleExternalDrop(
    dataTransfer: DataTransfer,
    targetParentId: string | null,
  ) {
    const items = dataTransfer.items;
    console.log("📥 [DragDrop] Traitement de", items?.length, "items dropés");
    if (!items) return;
    core.setLoading(true);
    try {
      for (let i = 0; i < items.length; i++) {
        const item = items[i].webkitGetAsEntry();
        if (item) {
          await uploadEntry(item, targetParentId);
        } else {
          console.log(
            "⚠️ [DragDrop] Impossible de convertir l'item",
            i,
            "via webkitGetAsEntry",
          );
        }
      }
      await fs.loadFileSystem();
    } finally {
      core.setLoading(false);
    }
  }

  return {
    createNewFile,
    uploadFiles,
    uploadFolderInput,
    handleExternalDrop,
  };
}

export function createSessionsStore(
  core: ReturnType<typeof createCoreStore>,
  editor: ReturnType<typeof createEditorStore>,
  artifacts: ReturnType<typeof createArtifactsStore>,
) {
  const [preparedSessions, setPreparedSessions] = createSignal<
    PreparedSession[]
  >([]);

  async function loadSessions() {
    try {
      const sessions = await core.runLobby((svc) => svc.fetchSessions);
      setPreparedSessions([...sessions]);
    } catch (e) {}
  }

  async function runSession(workflowId: string) {
    try {
      await core.runLobby((svc) => svc.startSession(workflowId));
      setTimeout(loadSessions, 2000);
    } catch (e) {
      alert(`Error starting session: ${core.errorMessage(e)}`);
    }
  }

  async function stopSession(workflowId: string) {
    if (!confirm("Stop this session?")) return;
    try {
      await core.runLobby((svc) => svc.stopSession(workflowId));
      setTimeout(loadSessions, 2000);
    } catch (e) {
      alert(`Error stopping session: ${core.errorMessage(e)}`);
    }
  }

  async function launchNomadJob(): Promise<boolean> {
    const fileId = editor.selectedFileId();
    const name = editor.selectedFileName();
    if (!fileId)
      return (
        alert("Please select a template from the file system first."),
        false
      );

    if (editor.stubWarningVisible()) {
      alert(
        `Le fichier "${name}" a encore le contenu par défaut. Ce n'est probablement pas ton vrai template. Sélectionne le bon fichier avant de lancer une session.`,
      );
      return false;
    }

    if (
      !confirm(
        `Lancer une session avec le template "${name}" et ${Object.keys(artifacts.selectedArtifacts()).length} artefact(s) sélectionné(s) ?`,
      )
    )
      return false;

    try {
      const art = Object.values(artifacts.selectedArtifacts()).map((a) => ({
        id: a.id,
        destination: a.destination,
      }));
      await core.runLobby((svc) => svc.launchNomadJob(fileId, art));
      await loadSessions();
      return true;
    } catch (e) {
      alert(`Error preparing job: ${core.errorMessage(e)}`);
      return false;
    }
  }

  return {
    preparedSessions,
    loadSessions,
    runSession,
    stopSession,
    launchNomadJob,
  };
}

export function createLobbyStore(projectId: string) {
  const core = createCoreStore(projectId);

  let artifactsStore: ReturnType<typeof createArtifactsStore>;
  let editorStore: ReturnType<typeof createEditorStore>;

  const fs = createFileSystemStore(core, {
    onNodeDeleted: (id) => {
      artifactsStore?.removeSelection(id);
      if (editorStore?.selectedFileId() === id) editorStore.clearEditor();
    },
  });

  artifactsStore = createArtifactsStore(fs);
  editorStore = createEditorStore(core, fs);
  const uploader = createUploaderStore(core, fs);
  const sessions = createSessionsStore(core, editorStore, artifactsStore);

  return {
    loading: core.loading,
    fileSystem: fs.fileSystem,
    flatMap: fs.flatMap,
    currentFolderId: fs.currentFolderId,
    selectedArtifacts: artifactsStore.selectedArtifacts,
    selectedFileId: editorStore.selectedFileId,
    selectedFileName: editorStore.selectedFileName,
    editorContent: editorStore.editorContent,
    setEditorContent: editorStore.setEditorContent,
    editorDisabled: editorStore.editorDisabled,
    preparedSessions: sessions.preparedSessions,
    stubWarningVisible: editorStore.stubWarningVisible,
    loadFileSystem: fs.loadFileSystem,
    loadSessions: sessions.loadSessions,
    getAllFileNodes: fs.getAllFileNodes,
    createNewFile: uploader.createNewFile,
    saveCurrentFile: editorStore.saveCurrentFile,
    promptCreateFolder: fs.promptCreateFolder,
    uploadFiles: uploader.uploadFiles,
    uploadFolderInput: uploader.uploadFolderInput,
    handleExternalDrop: uploader.handleExternalDrop,
    renameItem: fs.renameItem,
    clearEditor: editorStore.clearEditor,
    deleteItem: fs.deleteItem,
    moveItem: fs.moveItem,
    navigateTo: fs.navigateTo,
    toggleArtifactSelection: artifactsStore.toggleArtifactSelection,
    removeSelection: artifactsStore.removeSelection,
    updateArtifactDest: artifactsStore.updateArtifactDest,
    selectFile: editorStore.selectFile,
    launchNomadJob: sessions.launchNomadJob,
    runSession: sessions.runSession,
    stopSession: sessions.stopSession,
  };
}

export type LobbyStore = ReturnType<typeof createLobbyStore>;
