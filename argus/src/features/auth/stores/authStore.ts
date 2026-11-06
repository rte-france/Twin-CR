/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { invoke } from "@tauri-apps/api/core";
import { createStore } from "solid-js/store";
import { createMemo } from "solid-js";
import { getConfigSync } from "@/hooks/useConfig";

export interface JwtPayload {
  exp?: number;
  iss?: string;
  azp?: string;
  preferred_username?: string;
  name?: string;
  given_name?: string;
  email?: string;
  resource_access?: Record<string, { roles?: string[] }>;
  [key: string]: unknown;
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  error: string | null;
}

const [authStore, setAuthStore] = createStore<AuthState>({
  accessToken: localStorage.getItem("access_token"),
  refreshToken: localStorage.getItem("refresh_token"),
  error: null,
});

export const parseJwt = (token: string): JwtPayload | null => {
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const base64 = part.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join(""),
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
};

export const accessToken = () => authStore.accessToken;
export const refreshToken = () => authStore.refreshToken;
export const authError = () => authStore.error;

export const setAuthError = (error: string | null) => {
  setAuthStore("error", error);
};

export const setAccessToken = (token: string | null) => {
  setAuthStore("accessToken", token);
  if (token) {
    setAuthStore("error", null);
    localStorage.setItem("access_token", token);
  } else {
    localStorage.removeItem("access_token");
  }
};

export const setRefreshToken = (token: string | null) => {
  setAuthStore("refreshToken", token);
  if (token) localStorage.setItem("refresh_token", token);
  else localStorage.removeItem("refresh_token");
};

export const tokenParsed = createMemo<JwtPayload | null>(() => {
  const token = authStore.accessToken;
  return token ? parseJwt(token) : null;
});

export const getUsernameFromToken = (token: string | null): string => {
  if (!token) return "User";
  const parsed = parseJwt(token);
  return parsed?.preferred_username || parsed?.name || parsed?.given_name || "User";
};

export const isTokenExpired = (): boolean => {
  const parsed = tokenParsed();
  if (!parsed?.exp) return true;
  return Date.now() > parsed.exp * 1000 - 30000;
};

let refreshPromise: Promise<string | null> | null = null;

export const getValidToken = async (): Promise<string | null> => {
  if (!isTokenExpired()) {
    return authStore.accessToken;
  }

  const currentRefresh = authStore.refreshToken;
  const currentAccess = authStore.accessToken;
  if (!currentRefresh || !currentAccess) {
    setAccessToken(null);
    return null;
  }

  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const parsedToken = parseJwt(currentAccess);
      const config = getConfigSync();
      const issuer = parsedToken?.iss;
      const clientId = parsedToken?.azp || config.keycloakClientId;
      const baseUrl = issuer || `${config.keycloakUrl}/realms/${config.keycloakRealm}`;
      const tokenEndpoint = `${baseUrl}/protocol/openid-connect/token`;

      const response = await invoke<string>("refresh_token", {
        refreshToken: currentRefresh,
        clientId,
        tokenUrl: tokenEndpoint,
      });

      const tokens = JSON.parse(response);
      setAccessToken(tokens.access_token);
      if (tokens.refresh_token) {
        setRefreshToken(tokens.refresh_token);
      }
      return tokens.access_token as string;
    } catch (error) {
      const msg =
        typeof error === "object" && error !== null && "message" in error
          ? String((error as { message: unknown }).message)
          : String(error);
      setAuthError(msg);
      setAccessToken(null);
      setRefreshToken(null);
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
};
