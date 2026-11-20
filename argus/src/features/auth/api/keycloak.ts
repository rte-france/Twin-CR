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
import { Effect } from "effect";
import { getSystemRuntime } from "@/utils/getSystemRuntime";
import { Settings } from "@/services/settings";
import { SETTINGS } from "@/config/settings";
import {
  setAccessToken,
  setAuthError,
  setRefreshToken,
} from "../stores/authStore";

export interface KeycloakConfig {
  keycloakUrl: string;
  keycloakRealm: string;
  keycloakClientId: string;
  oauthDevPort: number;
}

const getKeycloakDefault = (key: string): any =>
  SETTINGS.find((s) => s.id === "keycloak")?.fields.find((f) => f.key === key)
    ?.defaultValue;

let cachedSettings: Record<string, any> = {};

// Keep cachedSettings up-to-date from the Settings service
listen<Record<string, any>>("settings-changed", (event) => {
  cachedSettings = event.payload;
  // Clear any temporary session override when settings change
  sessionStorage.removeItem("oauth_keycloak_url");
});

export const loadKeycloakConfig = async (): Promise<KeycloakConfig> => {
  try {
    const settings = await getSystemRuntime().runPromise(
      Effect.gen(function* () {
        const service = yield* Settings;
        return yield* service.loadSettings;
      }),
    );
    cachedSettings = settings;
  } catch (e) {
    console.warn(
      "[Auth] Failed to load settings from service, using cache/defaults",
      e,
    );
  }
  return getKeycloakConfig();
};

export const getKeycloakConfig = (): KeycloakConfig => {
  const customUrl = sessionStorage.getItem("oauth_keycloak_url");
  const kcSection = cachedSettings.keycloak || {};
  return {
    keycloakUrl:
      customUrl ||
      kcSection.keycloak_url ||
      cachedSettings.keycloak_url ||
      getKeycloakDefault("keycloak_url"),
    keycloakRealm:
      kcSection.keycloak_realm ||
      cachedSettings.keycloak_realm ||
      getKeycloakDefault("keycloak_realm"),
    keycloakClientId:
      kcSection.keycloak_client_id ||
      cachedSettings.keycloak_client_id ||
      getKeycloakDefault("keycloak_client_id"),
    oauthDevPort: Number(
      kcSection.oauth_dev_port ||
        cachedSettings.oauth_dev_port ||
        getKeycloakDefault("oauth_dev_port"),
    ),
  };
};

export const setCustomKeycloakUrl = (url: string): void => {
  sessionStorage.setItem("oauth_keycloak_url", url);
};

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
  return "Unknown error occurred";
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
  return Array.from(array, (dec) => ("0" + dec.toString(16)).slice(-2)).join(
    "",
  );
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

export const loginWithKeycloak = async (
  config?: Partial<KeycloakConfig>,
): Promise<void> => {
  const resolvedConfig = { ...getKeycloakConfig(), ...config };
  setAuthError(null);
  const state = generateRandomString();
  const verifier = generateRandomString();

  sessionStorage.setItem("oauth_state", state);
  sessionStorage.setItem("oauth_verifier", verifier);
  sessionStorage.setItem("oauth_keycloak_url", resolvedConfig.keycloakUrl);
  // Potential left over of an earlier attempt
  sessionStorage.removeItem("oauth_redirect_uri");

  const challenge = await generateCodeChallenge(verifier);

  let redirectUri = "twincr://login";
  const devPort = resolvedConfig.oauthDevPort;
  try {
    const activePort = await invoke<number>("start_oauth_server", {
      port: devPort,
    });
    if (activePort > 0) {
      redirectUri = `http://localhost:${activePort}`;
      sessionStorage.setItem("oauth_redirect_uri", redirectUri);
    }
  } catch (e) {
    console.warn(
      "Failed to start local oauth server, falling back to twincr://login",
      e,
    );
  }

  const params = new URLSearchParams({
    client_id: resolvedConfig.keycloakClientId,
    response_type: "code",
    redirect_uri: redirectUri,
    scope: "openid profile email",
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  const authUrl = `${resolvedConfig.keycloakUrl}/realms/${resolvedConfig.keycloakRealm}/protocol/openid-connect/auth?${params}`;

  await openUrl(authUrl);
};

let isInitialized = false;
let exchangingCode: string | null = null;

export const initAuth = (): void => {
  if (isInitialized) return;
  isInitialized = true;

  // Trigger initial settings fetch to populate cachedSettings
  loadKeycloakConfig();

  const handleAuthRedirect = async (deepLinkUrl: string) => {
    try {
      console.debug("[Auth] Handling redirect URL:", deepLinkUrl);
      const url = new URL(deepLinkUrl);
      const code = url.searchParams.get("code");
      const state = url.searchParams.get("state");

      const savedState = sessionStorage.getItem("oauth_state");
      const verifier = sessionStorage.getItem("oauth_verifier");

      // No saved state means no login was started from this window (or it already
      // completed): reject rather than exchange a code we did not ask for.
      if (!code || !savedState || state !== savedState) {
        console.warn(
          "[Auth] Code missing or state mismatch, skipping exchange",
        );
        return;
      }

      if (exchangingCode === code) {
        console.debug(
          "[Auth] Code already being exchanged, ignoring duplicate event",
        );
        return;
      }
      exchangingCode = code;

      const config = getKeycloakConfig();
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
    console.debug("[Auth] Event deep-link-received payload:", event.payload);
    handleAuthRedirect(event.payload);
  });
};
