importScripts('config.js');

const CONFIG = globalThis.ZERO_KEY_CONFIG;
const DEVICE_ID_KEY = 'device_id';
const ACCESS_TOKEN_KEY = 'auth0_access_token';
const ACCESS_TOKEN_EXPIRY_KEY = 'auth0_access_token_expiry';
const TELEMETRY_API_URL = `${CONFIG.apiOrigin.replace(/\/+$/, '')}/api/telemetry`;
const PUBLIC_IP_CACHE_KEY = 'public_ip_cache';
const PUBLIC_IP_CACHE_DURATION_MS = 15 * 60 * 1000;
const ALLOWED_PORTAL_ORIGINS = new Set([
  'http://localhost:5500',
  'http://127.0.0.1:5500',
  CONFIG.portalOrigin,
]);

function base64Url(bytes) {
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function randomBase64Url(byteLength) {
  return base64Url(crypto.getRandomValues(new Uint8Array(byteLength)));
}

function authConfigIsValid() {
  return (
    /^[A-Za-z0-9.-]+\.auth0\.com$/.test(CONFIG.auth0Domain) &&
    /^[A-Za-z0-9_-]+$/.test(CONFIG.auth0ClientId) &&
    CONFIG.auth0Audience.trim().length > 0
  );
}

async function loginWithAuth0() {
  if (!authConfigIsValid()) {
    throw new Error('Auth0 domain, client ID, and API audience must be configured first.');
  }

  const auth0Origin = `https://${CONFIG.auth0Domain}`;
  const apiOrigin = new URL(CONFIG.apiOrigin).origin;
  const portalOrigin = new URL(CONFIG.portalOrigin).origin;
  const requiredOrigins = [
    `${auth0Origin}/*`,
    `${apiOrigin}/*`,
    `${portalOrigin}/*`,
  ];
  const hasPermissions = await chrome.permissions.contains({ origins: requiredOrigins });
  if (!hasPermissions) {
    throw new Error('Grant the extension access to the configured portal, API, and Auth0 origins.');
  }

  const redirectUri = chrome.identity.getRedirectURL();
  const state = randomBase64Url(32);
  const verifier = randomBase64Url(64);
  const challenge = base64Url(
    new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))),
  );
  const authorizeUrl = new URL(`${auth0Origin}/authorize`);
  authorizeUrl.search = new URLSearchParams({
    response_type: 'code',
    client_id: CONFIG.auth0ClientId,
    redirect_uri: redirectUri,
    scope: 'openid',
    audience: CONFIG.auth0Audience,
    code_challenge: challenge,
    code_challenge_method: 'S256',
    state,
  }).toString();

  const callback = await chrome.identity.launchWebAuthFlow({
    url: authorizeUrl.toString(),
    interactive: true,
  });
  if (!callback) {
    throw new Error('Auth0 did not return an extension sign-in callback.');
  }
  const callbackUrl = new URL(callback);
  if (callbackUrl.searchParams.get('state') !== state) {
    throw new Error('Auth0 returned a mismatched sign-in state.');
  }
  const authCode = callbackUrl.searchParams.get('code');
  if (!authCode) {
    throw new Error(callbackUrl.searchParams.get('error_description') || 'Auth0 sign-in was denied.');
  }

  const tokenResponse = await fetch(`${auth0Origin}/oauth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      grant_type: 'authorization_code',
      client_id: CONFIG.auth0ClientId,
      code: authCode,
      redirect_uri: redirectUri,
      code_verifier: verifier,
    }),
  });
  if (!tokenResponse.ok) {
    throw new Error(`Auth0 token exchange returned HTTP ${tokenResponse.status}.`);
  }
  const tokenResult = await tokenResponse.json();
  if (typeof tokenResult.access_token !== 'string' || typeof tokenResult.expires_in !== 'number') {
    throw new Error('Auth0 returned an invalid access token response.');
  }

  await chrome.storage.session.set({
    [ACCESS_TOKEN_KEY]: tokenResult.access_token,
    [ACCESS_TOKEN_EXPIRY_KEY]: Date.now() + tokenResult.expires_in * 1000,
  });
  let accessCheck;
  try {
    accessCheck = await fetch(`${CONFIG.apiOrigin.replace(/\/+$/, '')}/api/auth/check`, {
      headers: { Authorization: `Bearer ${tokenResult.access_token}` },
    });
  } catch (error) {
    await chrome.storage.session.remove([ACCESS_TOKEN_KEY, ACCESS_TOKEN_EXPIRY_KEY]);
    throw error;
  }
  if (!accessCheck.ok) {
    await chrome.storage.session.remove([ACCESS_TOKEN_KEY, ACCESS_TOKEN_EXPIRY_KEY]);
    throw new Error(`The API did not approve this identity (HTTP ${accessCheck.status}).`);
  }
  await registerHostedPortalScript();
  return true;
}

async function getAccessToken() {
  const saved = await chrome.storage.session.get([
    ACCESS_TOKEN_KEY,
    ACCESS_TOKEN_EXPIRY_KEY,
  ]);
  if (
    typeof saved[ACCESS_TOKEN_KEY] !== 'string' ||
    typeof saved[ACCESS_TOKEN_EXPIRY_KEY] !== 'number' ||
    saved[ACCESS_TOKEN_EXPIRY_KEY] <= Date.now() + 30_000
  ) {
    throw new Error('Sign in from the extension popup before collecting telemetry.');
  }
  return saved[ACCESS_TOKEN_KEY];
}

async function registerHostedPortalScript() {
  const portal = new URL(CONFIG.portalOrigin);
  if (portal.protocol !== 'https:' || !portal.hostname.endsWith('.onrender.com')) {
    return;
  }

  async function unregisterHostedPortalScript() {
    const registered = await chrome.scripting.getRegisteredContentScripts({
      ids: ['zerokey-hosted-portal'],
    });
    if (registered.length) {
      await chrome.scripting.unregisterContentScripts({ ids: ['zerokey-hosted-portal'] });
    }
  }

  const originPattern = `${portal.origin}/*`;
  if (!(await chrome.permissions.contains({ origins: [originPattern] }))) {
    return;
  }

  const registered = await chrome.scripting.getRegisteredContentScripts({
    ids: ['zerokey-hosted-portal'],
  });
  if (registered.length) {
    await chrome.scripting.unregisterContentScripts({ ids: ['zerokey-hosted-portal'] });
  }
  await chrome.scripting.registerContentScripts([
    {
      id: 'zerokey-hosted-portal',
      matches: [originPattern],
      js: ['config.js', 'content.js'],
      runAt: 'document_start',
      persistAcrossSessions: true,
    },
  ]);
}

async function getDeviceId() {
  const stored = await chrome.storage.local.get(DEVICE_ID_KEY);
  if (typeof stored[DEVICE_ID_KEY] === 'string') {
    return stored[DEVICE_ID_KEY];
  }

  const randomId = crypto.randomUUID();
  const digest = await crypto.subtle.digest(
    'SHA-256',
    new TextEncoder().encode(randomId),
  );
  const deviceId = Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
  await chrome.storage.local.set({ [DEVICE_ID_KEY]: deviceId });
  return deviceId;
}

async function forwardTelemetry(payload) {
  const accessToken = await getAccessToken();
  let publicIpAddress = null;
  try {
    publicIpAddress = await getPublicIpAddress();
  } catch (error) {
    console.warn('Public IP lookup failed; sending behavioral features without an IP.', error);
  }

  const deviceId = await getDeviceId();
  const response = await fetch(TELEMETRY_API_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...payload,
      device_id: deviceId,
      public_ip_address: publicIpAddress,
    }),
  });

  if (!response.ok) {
    const responseBody = await response.text();
    let detail = responseBody;
    try {
      const errorResponse = JSON.parse(responseBody);
      if (Array.isArray(errorResponse.detail)) {
        detail = errorResponse.detail
          .map((item) => {
            const location = Array.isArray(item.loc) ? item.loc.join('.') : 'request';
            return `${location}: ${item.msg || 'invalid value'}`;
          })
          .join('; ');
      } else if (typeof errorResponse.detail === 'string') {
        detail = errorResponse.detail;
      }
    } catch {
      // Preserve non-JSON error responses for troubleshooting.
    }
    throw new Error(`Telemetry API returned HTTP ${response.status}: ${detail}`);
  }
}

async function getPublicIpAddress() {
  const cached = await chrome.storage.session.get(PUBLIC_IP_CACHE_KEY);
  const cachedIp = cached[PUBLIC_IP_CACHE_KEY];
  if (
    cachedIp &&
    typeof cachedIp.address === 'string' &&
    typeof cachedIp.fetchedAt === 'number' &&
    Date.now() - cachedIp.fetchedAt < PUBLIC_IP_CACHE_DURATION_MS
  ) {
    return cachedIp.address;
  }

  const response = await fetch('https://api.ipify.org?format=json', {
    signal: AbortSignal.timeout(5_000),
  });
  if (!response.ok) {
    throw new Error(`Public IP lookup returned HTTP ${response.status}.`);
  }
  const result = await response.json();
  if (typeof result.ip !== 'string') {
    throw new Error('Public IP lookup returned an invalid response.');
  }
  await chrome.storage.session.set({
    [PUBLIC_IP_CACHE_KEY]: { address: result.ip, fetchedAt: Date.now() },
  });
  return result.ip;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const senderOrigin = sender.tab?.url ? new URL(sender.tab.url).origin : null;
  if (message?.type === 'auth-login') {
    if (sender.tab || sender.url !== chrome.runtime.getURL('popup.html')) {
      sendResponse({ ok: false, error: 'Sign-in must be started from the extension popup.' });
      return false;
    }
    loginWithAuth0().then(
      () => sendResponse({ ok: true }),
      (error) => {
        console.error('Auth0 extension sign-in failed.', error);
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : 'Auth0 sign-in failed.',
        });
      },
    );
    return true;
  }

  if (message?.type === 'auth-logout') {
    if (sender.tab || sender.url !== chrome.runtime.getURL('popup.html')) {
      sendResponse({ ok: false, error: 'Sign-out must be started from the extension popup.' });
      return false;
    }
    chrome.storage.session.remove([ACCESS_TOKEN_KEY, ACCESS_TOKEN_EXPIRY_KEY]).then(
      () => unregisterHostedPortalScript().then(
        () => sendResponse({ ok: true }),
        (error) => {
          console.error('Unable to unregister the hosted portal after sign-out.', error);
          sendResponse({ ok: false, error: 'Signed out, but portal access cleanup failed.' });
        },
      ),
      (error) => {
        console.error('Unable to clear the extension sign-in session.', error);
        sendResponse({ ok: false, error: 'Unable to clear the sign-in session.' });
      },
    );
    return true;
  }

  if (message?.type === 'telemetry-ready') {
    if (!senderOrigin || !ALLOWED_PORTAL_ORIGINS.has(senderOrigin)) {
      sendResponse({ ok: false, error: 'Request did not originate from the configured portal.' });
      return false;
    }
    getAccessToken().then(
      () => sendResponse({ ok: true }),
      (error) => {
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : 'Extension sign-in is required.',
        });
      },
    );
    return true;
  }

  if (message?.type === 'get-device-id') {
    if (!senderOrigin || !ALLOWED_PORTAL_ORIGINS.has(senderOrigin)) {
      sendResponse({ ok: false, error: 'Request did not originate from the portal.' });
      return false;
    }
    getDeviceId().then(
      (deviceId) => sendResponse({ ok: true, device_id: deviceId }),
      (error) => {
        console.error('Unable to initialize the privacy-preserving device ID.', error);
        sendResponse({ ok: false, error: 'Device ID initialization failed.' });
      },
    );
    return true;
  }

  if (message?.type === 'telemetry-window') {
    if (
      !senderOrigin ||
      !ALLOWED_PORTAL_ORIGINS.has(senderOrigin) ||
      typeof message.payload !== 'object' ||
      message.payload === null
    ) {
      sendResponse({ ok: false, error: 'Invalid telemetry message.' });
      return false;
    }

    forwardTelemetry(message.payload).then(
      () => sendResponse({ ok: true }),
      (error) => {
        console.error('Unable to send behavioral telemetry to the configured API.', error);
        sendResponse({
          ok: false,
          error: error instanceof Error ? error.message : 'Telemetry delivery failed.',
        });
      },
    );
    return true;
  }

  return false;
});
