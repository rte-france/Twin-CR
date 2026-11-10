/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

export interface FileNode {
	id: string;
	name: string;
	is_directory: boolean;
	children?: FileNode[];
	// Champ interne ajouté côté client pour remonter facilement vers le parent
	// (équivalent du node._parentId dans le script original).
	_parentId?: string | null;
}

export interface FlatMap {
	[id: string]: FileNode;
}

export interface SelectedArtifact {
	id: string;
	name: string;
	destination: string;
}

export interface SelectedArtifactsMap {
	[id: string]: SelectedArtifact;
}

export type SessionStatus = "RUNNING" | "STOPPED" | string;

export interface PreparedSession {
	id: string;
	name: string;
	status: SessionStatus;
}

export interface FileNodeInfo {
	file: FileNode;
	path: string;
}
