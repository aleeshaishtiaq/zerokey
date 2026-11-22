import { createAuth0Client } from '@auth0/auth0-spa-js';

const domain = import.meta.env.VITE_AUTH0_DOMAIN?.trim();
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID?.trim();
const audience = import.meta.env.VITE_AUTH0_AUDIENCE?.trim();
const apiBaseUrl = (
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8765'
).trim().replace(/\/+$/, '');

let auth0Client;
let auth0ClientPromise;

function sharePortalAccessToken(tokenResult) {
  if (
    typeof tokenResult?.access_token !== 'string' ||
    typeof tokenResult.expires_in !== 'number'
  ) {
    throw new Error('Auth0 did not return a usable API access token.');
  }
  window.postMessage(
    {
      source: 'zerokey-portal',
      type: 'telemetry-auth',
      accessToken: tokenResult.access_token,
      expiresAt: Date.now() + tokenResult.expires_in * 1000,
    },
    window.location.origin,
  );
}

export async function initializePortalAuth(onAuthorized, setStatus) {
  if (!domain || !clientId || !audience || !apiBaseUrl) {
    setStatus('Staging authentication is not configured. Access is denied.');
    return;
  }

  try {
    setStatus('Connecting to Auth0…');
    auth0ClientPromise = createAuth0Client({
      domain,
      clientId,
      authorizationParams: {
        audience,
        redirect_uri: `${window.location.origin}/`,
        scope: 'openid',
      },
      cacheLocation: 'memory',
      useRefreshTokens: false,
    });
    auth0Client = await auth0ClientPromise;

    const callbackParams = new URLSearchParams(window.location.search);
    const callbackError = callbackParams.get('error');
    if (callbackError) {
      const description = callbackParams.get('error_description');
      window.history.replaceState({}, document.title, window.location.pathname);
      setStatus(
        description
          ? `Auth0 sign-in failed: ${description}`
          : `Auth0 sign-in failed: ${callbackError}`,
      );
      return;
    }

    if (callbackParams.has('code') && callbackParams.has('state')) {
      setStatus('Completing Auth0 sign-in…');
      await auth0Client.handleRedirectCallback();
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    setStatus('Checking Auth0 sign-in status…');
    if (!(await auth0Client.isAuthenticated())) {
      setStatus('Sign in with an identity approved for this portal.');
      return;
    }

    setStatus('Requesting an access token…');
    const tokenResult = await auth0Client.getTokenSilently({ detailedResponse: true });
    setStatus('Checking authorization with the configured API…');
    const accessCheck = await fetch(`${apiBaseUrl}/api/auth/check`, {
      headers: { Authorization: `Bearer ${tokenResult.access_token}` },
      signal: AbortSignal.timeout(10_000),
    });
    if (!accessCheck.ok) {
      let detail = '';
      try {
        const result = await accessCheck.json();
        detail = typeof result.detail === 'string' ? result.detail : '';
      } catch {
        detail = '';
      }
      setStatus(
        detail
          ? `The configured API denied access (HTTP ${accessCheck.status}): ${detail}`
          : `The configured API denied access (HTTP ${accessCheck.status}).`,
      );
      return;
    }

    onAuthorized();
    if (localStorage.getItem('zerokeyTelemetryConsent') === 'granted') {
      sharePortalAccessToken(tokenResult);
    }
  } catch (error) {
    console.error('Auth0 sign-in could not be completed.', error);
    setStatus(
      error instanceof Error
        ? `Sign-in failed: ${error.message}`
        : 'Sign-in could not be completed. Please try again.',
    );
  }
}

export async function enablePortalTelemetry() {
  if (!auth0Client || !(await auth0Client.isAuthenticated())) {
    throw new Error('Sign in to the portal before enabling telemetry.');
  }
  const tokenResult = await auth0Client.getTokenSilently({ detailedResponse: true });
  sharePortalAccessToken(tokenResult);
}

export function disablePortalTelemetry() {
  window.postMessage(
    { source: 'zerokey-portal', type: 'telemetry-revoke' },
    window.location.origin,
  );
}

export async function beginPortalSignIn() {
  if (!auth0Client && auth0ClientPromise) {
    auth0Client = await auth0ClientPromise;
  }
  if (!auth0Client) {
    throw new Error('Auth0 is not configured for an approved staging identity.');
  }
  await auth0Client.loginWithRedirect();
}

export async function signOutPortal() {
  if (!auth0Client) {
    return;
  }
  await auth0Client.logout({
    logoutParams: { returnTo: `${window.location.origin}/` },
  });
}
