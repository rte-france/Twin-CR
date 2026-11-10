/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

export const BINARY_EXT = new Set([
	"png",
	"jpg",
	"jpeg",
	"gif",
	"webp",
	"ico",
	"bmp",
	"svgz",
	"tiff",
	"pdf",
	"zip",
	"tar",
	"gz",
	"tgz",
	"bz2",
	"xz",
	"7z",
	"rar",
	"exe",
	"bin",
	"so",
	"dll",
	"dylib",
	"o",
	"a",
	"jar",
	"class",
	"wasm",
	"woff",
	"woff2",
	"ttf",
	"otf",
	"eot",
	"mp3",
	"wav",
	"ogg",
	"flac",
	"mp4",
	"mov",
	"avi",
	"mkv",
	"webm",
	"xlsx",
	"xls",
	"docx",
	"doc",
	"pptx",
	"ppt",
	"odt",
	"ods",
	"sqlite",
	"sqlite3",
	"db",
	"pyc",
	"pack",
	"idx",
]);

export const CODE_EXT = new Set([
	"hcl",
	"tpl",
	"tf",
	"tfvars",
	"nomad",
	"json",
	"yaml",
	"yml",
	"toml",
	"ini",
	"conf",
	"cfg",
	"env",
	"properties",
	"sh",
	"bash",
	"zsh",
	"ps1",
	"bat",
	"py",
	"js",
	"mjs",
	"ts",
	"tsx",
	"jsx",
	"go",
	"rs",
	"rb",
	"java",
	"c",
	"h",
	"cpp",
	"hpp",
	"cs",
	"php",
	"lua",
	"sql",
	"graphql",
	"proto",
	"html",
	"htm",
	"css",
	"scss",
	"less",
	"xml",
	"svg",
	"md",
	"dockerfile",
]);

// Signature du contenu stub généré par defaultContentFor() pour hcl/nomad/tpl.
// Sert à détecter et avertir si un fichier ressemble encore au template vide
// par défaut ("group1" / "task1" / alpine:latest), pour éviter de lancer
// une session avec un fichier qui n'a jamais été rempli.
export const STUB_MARKERS = [
	'group "group1"',
	'task "task1"',
	'image = "alpine:latest"',
];

export function getExt(name: string): string {
	const base = name.split("/").pop() ?? "";
	const i = base.lastIndexOf(".");
	if (i <= 0) return "";
	return base.slice(i + 1).toLowerCase();
}

export function isEditableFile(name: string): boolean {
	return !BINARY_EXT.has(getExt(name));
}

export function iconFor(node: { is_directory: boolean; name: string }): string {
	if (node.is_directory) return "folder";
	const ext = getExt(node.name);
	if (BINARY_EXT.has(ext)) return "lock";
	if (CODE_EXT.has(ext)) return "data_object";
	return "description";
}

export function defaultContentFor(name: string): string {
	const ext = getExt(name);
	const stem = name.replace(/\.[^/.]+$/, "");

	if (ext === "hcl" || ext === "nomad" || ext === "tpl") {
		return `job "${stem}" {\n  datacenters = ["dc1"]\n\n  group "group1" {\n    task "task1" {\n      driver = "docker"\n      config {\n        image = "alpine:latest"\n      }\n    }\n  }\n}`;
	}
	if (ext === "json") return "{\n  \n}";
	if (ext === "yaml" || ext === "yml") return `# ${name}\n`;
	if (ext === "sh") return "#!/usr/bin/env bash\nset -euo pipefail\n\n";
	if (ext === "py") return `"""${name}"""\n\n`;
	if (ext === "md") return `# ${stem}\n\n`;
	return "";
}

// Détecte si un contenu ressemble encore au stub par défaut
// (job "group1" / task "task1" / alpine:latest).
export function looksLikeStub(content: string): boolean {
	return STUB_MARKERS.every((marker) => content.includes(marker));
}
