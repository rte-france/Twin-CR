/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

import { invoke } from "@tauri-apps/api/core";
import { onOpenUrl, getCurrent } from "@tauri-apps/plugin-deep-link";
import { openUrl } from "@tauri-apps/plugin-opener";
import { listen } from "@tauri-apps/api/event";
import { type AppConfig } from "@/services/config";
import { getConfigSync } from "@/hooks/useConfig";
import { setAccessToken, setAuthError, setRefreshToken } from "../stores/authStore";

export type AuthBackendError =
  | { _tag: "ClientInit"; message: string }
  | { _tag: "Network"; message: string }
  | { _tag: "AuthenticationRefused"; message: string }
  | { _tag: "ResponseBody"; message: string };

export const isAuthBackendError = (err: unknown): err is AuthBackendError => {
  return (
    typeof err === "object" &&
    err !== null &&
    "_tag" in err &&
    typeof (err as Record<string, unknown>)._tag === "string" &&
    "message" in err &&
    typeof (err as Record<string, unknown>).message === "string"
  );
};

export const getAuthErrorMessage = (err: unknown): string => {
  if (isAuthBackendError(err)) {
    return err.message;
  }
  if (err instanceof Error) {
    return err.message;
  }
  if (typeof err === "string") {
    return err;
  }
  return "Une erreur inconnue est survenue.";
};

interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  id_token?: string;
  expires_in?: number;
  token_type?: string;
}

const generateRandomString = (length = 28): string => {
  const array = new Uint32Array(length);
  window.crypto.getRandomValues(array);
  return Array.from(array, (dec) => ("0" + dec.toString(16)).slice(-2)).join("");
};

const generateCodeChallenge = async (verifier: string): Promise<string> => {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await window.crypto.subtle.digest("SHA-256", data);
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
};

export const loginWithKeycloak = async (config: AppConfig): Promise<void> => {
  setAuthError(null);
  const state = generateRandomString();
  const verifier = generateRandomString();

  sessionStorage.setItem("oauth_state", state);
  sessionStorage.setItem("oauth_verifier", verifier);
  sessionStorage.setItem("oauth_keycloak_url", config.keycloakUrl);
  // Potential left over of an earlier attempt
  sessionStorage.removeItem("oauth_redirect_uri");

  const challenge = await generateCodeChallenge(verifier);

  const isMac = navigator.userAgent.includes("Mac");
  const isDev = import.meta.env.DEV;
  const useOAuthServer = isMac && isDev;

  let redirectUri = "twincr://login";
  if (useOAuthServer) {
    const devPort = config.oauthDevPort;
    try {
      await invoke<number>("start_oauth_server", { port: devPort });
      redirectUri = `http://localhost:${devPort}`;
      sessionStorage.setItem("oauth_redirect_uri", redirectUri);
    } catch (e) {
      console.warn("Failed to start local oauth server, falling back to twincr://login", e);
    }
  }

  const params = new URLSearchParams({
    client_id: config.keycloakClientId,
    response_type: "code",
    redirect_uri: redirectUri,
    scope: "openid profile email",
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  const authUrl = `${config.keycloakUrl}/realms/${config.keycloakRealm}/protocol/openid-connect/auth?${params}`;

  await openUrl(authUrl);
};

let isInitialized = false;
let exchangingCode: string | null = null;

export const initAuth = (): void => {
  if (isInitialized) return;
  isInitialized = true;

  const handleAuthRedirect = async (deepLinkUrl: string) => {
    try {
      console.log("[Auth] Handling redirect URL:", deepLinkUrl);
      const url = new URL(deepLinkUrl);
      const code = url.searchParams.get("code");
      const state = url.searchParams.get("state");

      const savedState = sessionStorage.getItem("oauth_state");
      const verifier = sessionStorage.getItem("oauth_verifier");

      console.log("[Auth] Code present:", !!code, "State:", state, "SavedState:", savedState);

      // No saved state means no login was started from this window (or it already
      // completed): reject rather than exchange a code we did not ask for.
      if (!code || !savedState || state !== savedState) {
        console.warn("[Auth] Code missing or state mismatch, skipping exchange");
        return;
      }

      if (exchangingCode === code) {
        console.log("[Auth] Code already being exchanged, ignoring duplicate event");
        return;
      }
      exchangingCode = code;

      const config = getConfigSync();
      const tokenEndpoint = `${config.keycloakUrl}/realms/${config.keycloakRealm}/protocol/openid-connect/token`;
      const savedRedirectUri = sessionStorage.getItem("oauth_redirect_uri");

      console.log("[Auth] Exchanging code with token endpoint:", tokenEndpoint);

      const tokenResponse = await invoke<string>("exchange_code", {
        code,
        clientId: config.keycloakClientId,
        tokenUrl: tokenEndpoint,
        codeVerifier: verifier || "",
        redirectUri: savedRedirectUri || undefined,
      });

      const tokens: TokenResponse = JSON.parse(tokenResponse);
      console.log("[Auth] Token exchange success:", !!tokens.access_token);

      sessionStorage.removeItem("oauth_state");
      sessionStorage.removeItem("oauth_verifier");
      sessionStorage.removeItem("oauth_redirect_uri");
      sessionStorage.removeItem("oauth_keycloak_url");

      setAccessToken(tokens.access_token);
      if (tokens.refresh_token) {
        setRefreshToken(tokens.refresh_token);
      }
    } catch (e) {
      if (isAuthBackendError(e)) {
        console.error(`[Auth] Backend error (${e._tag}):`, e.message);
      } else {
        console.error("[Auth] Unexpected error during token exchange:", e);
      }
      setAuthError(getAuthErrorMessage(e));
    } finally {
      exchangingCode = null;
    }
  };

  getCurrent().then((startUrls) => {
    if (startUrls && startUrls.length > 0) {
      handleAuthRedirect(startUrls[0]);
    }
  });

  onOpenUrl((urls) => {
    if (urls && urls.length > 0) {
      handleAuthRedirect(urls[0]);
    }
  });

  listen<string>("deep-link-received", (event) => {
    console.log("[Auth] Event deep-link-received payload:", event.payload);
    handleAuthRedirect(event.payload);
  });
};
