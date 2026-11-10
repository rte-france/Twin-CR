/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import {
	FiBox,
	FiChevronDown,
	FiChevronRight,
	FiFileText,
	FiFolder,
	FiX,
} from "solid-icons/fi";
import { type Component, createMemo, createSignal, For, Show } from "solid-js";
import type { LobbyStore } from "@/features/workspace/hooks/store";

type TreeFolder = {
	name: string;
	path: string;
	folders: Record<string, TreeFolder>;
	files: any[];
};

const SelectedArtifactsPanel: Component<{ store: LobbyStore }> = (props) => {
	const [collapsed, setCollapsed] = createSignal<Set<string>>(new Set());

	const toggleNode = (path: string) => {
		setCollapsed((prev) => {
			const next = new Set(prev);
			if (next.has(path)) next.delete(path);
			else next.add(path);
			return next;
		});
	};

	const fileTree = createMemo(() => {
		const artifacts = Object.values(props.store.selectedArtifacts());
		const root: TreeFolder = {
			name: "Root",
			path: "root",
			folders: {},
			files: [],
		};

		artifacts.forEach((art) => {
			const dest = art.destination?.trim().replace(/^\/+/, "") || "";
			const parts = dest.split("/").filter(Boolean);

			let current = root;
			let currentPath = "root";

			parts.forEach((part) => {
				currentPath += `/${part}`;
				if (!current.folders[part]) {
					current.folders[part] = {
						name: part,
						path: currentPath,
						folders: {},
						files: [],
					};
				}
				current = current.folders[part];
			});

			current.files.push(art);
		});

		const sortFolder = (folder: TreeFolder) => {
			folder.files.sort((a, b) => a.name.localeCompare(b.name));
			Object.values(folder.folders).forEach(sortFolder);
		};
		sortFolder(root);

		return root;
	});

	const getFolderFileIds = (folder: TreeFolder): string[] => {
		const ids = folder.files.map((f) => f.id);
		Object.values(folder.folders).forEach((sub) => {
			ids.push(...getFolderFileIds(sub));
		});
		return ids;
	};

	const FolderNode: Component<{ folder: TreeFolder; level: number }> = (p) => {
		const sortedFolders = () =>
			Object.values(p.folder.folders).sort((a, b) =>
				a.name.localeCompare(b.name),
			);
		const isOpen = () => !collapsed().has(p.folder.path);

		return (
			<div class="flex flex-col">
				<Show when={p.level >= 0}>
					<div
						class="group flex items-center justify-between h-7 pr-2 cursor-pointer bg-white/95 backdrop-blur-sm sticky z-10 border-b border-gray-50 hover:bg-gray-100 transition-colors"
						style={{
							"padding-left": `${p.level * 16 + 12}px`,
							top: `${p.level * 28}px`,
						}}
						onClick={() => toggleNode(p.folder.path)}
					>
						<div class="flex items-center gap-1.5 overflow-hidden">
							<span class="w-4 flex justify-center shrink-0 text-gray-400">
								{isOpen() ? (
									<FiChevronDown class="text-sm" />
								) : (
									<FiChevronRight class="text-sm" />
								)}
							</span>
							<FiFolder class="text-blue-500 text-sm shrink-0" />
							<span class="text-[12px] font-medium text-gray-800 truncate select-none">
								{p.folder.name}
							</span>
						</div>
						<button
							type="button"
							class="p-0.5 text-gray-400 opacity-0 group-hover:opacity-100 hover:text-red-600 hover:bg-red-50 rounded transition-all shrink-0"
							onClick={(e) => {
								e.stopPropagation();
								const idsToRemove = getFolderFileIds(p.folder);
								idsToRemove.forEach((id) => props.store.removeSelection(id));
							}}
						>
							<FiX class="text-xs" />
						</button>
					</div>
				</Show>

				<Show when={isOpen() || p.level === -1}>
					<div class="flex flex-col">
						<For each={sortedFolders()}>
							{(subFolder) => (
								<FolderNode folder={subFolder} level={p.level + 1} />
							)}
						</For>

						<For each={p.folder.files}>
							{(art) => (
								<div
									class="group flex items-center justify-between h-7 pr-2 hover:bg-blue-50 transition-colors"
									style={{ "padding-left": `${(p.level + 1) * 16 + 12}px` }}
								>
									<div class="flex items-center gap-1.5 text-[12px] text-gray-600 truncate">
										<span class="w-4 shrink-0"></span>
										<FiFileText class="text-gray-400 text-sm shrink-0" />
										<span class="truncate select-none" title={art.name}>
											{art.name}
										</span>
									</div>
									<button
										class="p-0.5 text-gray-400 opacity-0 group-hover:opacity-100 hover:text-red-600 hover:bg-red-50 rounded transition-all shrink-0"
										onClick={() => props.store.removeSelection(art.id)}
									>
										<FiX class="text-xs" />
									</button>
								</div>
							)}
						</For>
					</div>
				</Show>
			</div>
		);
	};

	return (
		<div class="flex flex-col flex-1 min-h-0 bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
			<div class="flex items-center gap-2 px-3 py-2.5 font-semibold text-gray-700 bg-gray-50 border-b border-gray-200 shrink-0 relative z-20">
				<FiBox class="text-blue-600" />
				Selected Artifacts
			</div>

			<div class="flex-1 overflow-y-auto bg-white pb-2 relative">
				<Show
					when={Object.keys(props.store.selectedArtifacts()).length > 0}
					fallback={
						<div class="p-5 text-center text-sm text-gray-400 italic">
							Select files or folders from the file system to inject them.
						</div>
					}
				>
					<FolderNode folder={fileTree()} level={-1} />
				</Show>
			</div>
		</div>
	);
};

export default SelectedArtifactsPanel;
