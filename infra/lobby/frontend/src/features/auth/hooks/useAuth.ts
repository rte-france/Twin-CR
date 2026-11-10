/*
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
*/

import { kc } from "../api/keycloak";

export const useAuth = () => {
  const user = () => ({
    username: kc.tokenParsed?.preferred_username || kc.tokenParsed?.name || "User",
    email: kc.tokenParsed?.email || "",
    initial: (kc.tokenParsed?.preferred_username || kc.tokenParsed?.name || "U").charAt(0).toUpperCase()
  });

  return {
    user,
    tokenParsed: () => kc.tokenParsed,
    roles: () => kc.clientId ? kc.resourceAccess?.[kc.clientId]?.roles || [] : [],
    hasRole: (role: string) => kc.clientId ? kc.hasResourceRole(role, kc.clientId) : false,
    logout: () => kc.logout(),
    manageAccount: () => kc.accountManagement(),
  };
};
