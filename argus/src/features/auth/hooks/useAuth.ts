/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { createMemo } from "solid-js";
import { openUrl } from "@tauri-apps/plugin-opener";
import { getConfigSync, setCustomKeycloakUrl } from "@/hooks/useConfig";
import { tokenParsed, setAccessToken, setRefreshToken } from "../stores/authStore";

export const useAuth = () => {
  const getClientId = () => getConfigSync().keycloakClientId;

  const user = () => {
    const parsed = tokenParsed();
    return {
      username: parsed?.preferred_username || parsed?.name || "User",
      email: parsed?.email || "",
      initial: (parsed?.preferred_username || parsed?.name || "U")
        .charAt(0)
        .toUpperCase(),
    };
  };

  const hasRole = (role: string) => {
    const parsed = tokenParsed();
    return parsed?.resource_access?.[getClientId()]?.roles?.includes(role) ?? false;
  };

  const isTemplateManager = createMemo(() => hasRole("template_manager"));
  const isSessionLauncher = createMemo(() => hasRole("session_launcher"));
  const isParticipantGM = createMemo(() => hasRole("participant_gm"));
  const isParticipantOP = createMemo(() => hasRole("participant_operator"));

  const isAuthenticated = createMemo(() => {
    const parsed = tokenParsed();
    return !!parsed?.sub;
  });

  const logout = async () => {
    const config = getConfigSync();
    setAccessToken(null);
    setRefreshToken(null);
    sessionStorage.removeItem("oauth_verifier");
    sessionStorage.removeItem("oauth_state");
    sessionStorage.removeItem("oauth_redirect_uri");

    const logoutUrl = `${config.keycloakUrl}/realms/${config.keycloakRealm}/protocol/openid-connect/logout?client_id=${config.keycloakClientId}`;
    await openUrl(logoutUrl);
  };

  const manageAccount = async () => {
    const config = getConfigSync();
    const accountUrl = `${config.keycloakUrl}/realms/${config.keycloakRealm}/account/`;
    await openUrl(accountUrl);
  };

  return {
    user,
    tokenParsed: () => tokenParsed(),
    isAuthenticated,
    roles: () => {
      const parsed = tokenParsed();
      return parsed?.resource_access?.[getClientId()]?.roles || [];
    },
    hasRole,
    logout,
    manageAccount,
    setCustomKeycloakUrl,
    isTemplateManager,
    isSessionLauncher,
    isParticipantGM,
    isParticipantOP,
    username: () => user().username,
  };
};
