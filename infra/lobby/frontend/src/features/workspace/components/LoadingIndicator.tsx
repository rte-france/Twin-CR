/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { FiRefreshCw } from "solid-icons/fi";
import type { Component } from "solid-js";

const LoadingIndicator: Component<{ visible: boolean }> = (props) => {
	return (
		<div
			class={`absolute top-3 left-1/2 -translate-x-1/2 bg-white border border-gray-200 px-4 py-1.5 rounded-full text-xs font-medium flex items-center gap-2 shadow-md z-50 transition-opacity duration-200 ${
				props.visible ? "opacity-100" : "opacity-0 pointer-events-none"
			}`}
		>
			<FiRefreshCw class="animate-spin text-blue-600" />
			Processing...
		</div>
	);
};

export default LoadingIndicator;
