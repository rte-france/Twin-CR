/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { type Component, onMount } from "solid-js";
import { useParams } from "@solidjs/router";

import EditorPanel from "@/features/workspace/components/EditorPanel";
import FileSystemPanel from "@/features/workspace/components/FileSystemPanel";
import Header from "@/features/workspace/components/Header";
import LoadingIndicator from "@/features/workspace/components/LoadingIndicator";
import SelectedArtifactsPanel from "@/features/workspace/components/SelectedArtifactsPanel";
import SessionsPanel from "@/features/workspace/components/SessionsPanel";
import { createLobbyStore } from "@/features/workspace/hooks/store";

const Workspace: Component = () => {
  const params = useParams<{
    projectId: string;
    fileId?: string;
  }>();
  const store = createLobbyStore(params.projectId);

  onMount(async () => {
    await store.loadFileSystem();
    await store.loadSessions();

    if (params.fileId) {
      await store.selectFile(params.fileId);
    }
  });

  return (
    <div class="h-screen grid grid-cols-[320px_1fr_300px] bg-gray-50 grid-rows-[60px_1fr] text-gray-900 overflow-hidden relative font-sans">
      <LoadingIndicator visible={store.loading()} />

      <Header store={store} />

      <aside class="col-start-1 row-start-2 flex flex-col gap-3 p-3 border-r border-gray-200 h-full overflow-hidden">
        <FileSystemPanel store={store} />
        <SelectedArtifactsPanel store={store} />
      </aside>

      <div class="col-start-2 row-start-2 flex flex-col h-full overflow-hidden">
        <EditorPanel store={store} />
      </div>

      <SessionsPanel store={store} />
    </div>
  );
};

export default Workspace;
