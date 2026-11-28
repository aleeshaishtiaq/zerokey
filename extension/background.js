importScripts('config.js');

const CONFIG = globalThis.ZERO_KEY_CONFIG;
const DEVICE_ID_KEY = 'device_id';
const ACCESS_TOKEN_KEY = 'auth0_access_token';
const ACCESS_TOKEN_EXPIRY_KEY = 'auth0_access_token_expiry';
const TELEMETRY_CONSENT_KEY = 'telemetry_consent';
const PUBLIC_IP_KEY = 'public_ip_address';
const PUBLIC_IP_FETCHED_AT_KEY = 'public_ip_fetched_at';
const PUBLIC_IP_CACHE_TTL_MS = 15 * 60 * 1000;
const PUBLIC_IP_LOOKUP_PROVIDERS = [
  {
    name: 'ipify',
    url: 'https://api.ipify.org?format=json',
    readAddress: async (response) => (await response.json()).ip,
  },
  {
    name: 'Amazon checkip',
    url: 'https://checkip.amazonaws.com',
    readAddress: async (response) => response.text(),
  },
];
// Windows that could not be sent (sign-in expired, network or API down) are
// kept here and sent later, but only for the same signed-in user.
const PENDING_WINDOWS_KEY = 'pending_windows';
const LAST_SUBJECT_KEY = 'last_subject';
const MAX_PENDING_WINDOWS = 960; // about 4 hours of 15-second windows
const MAX_PENDING_AGE_MS = 24 * 60 * 60 * 1000;
const TELEMETRY_API_URL = `${CONFIG.apiOrigin.replace(/\/+$/, '')}/api/telemetry`;
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
    throw new Error('Sign in to the portal and enable telemetry before collecting activity.');
  }
  return saved[ACCESS_TOKEN_KEY];
}

async function registerHostedPortalScript() {
  const portal = new URL(CONFIG.portalOrigin);
  if (portal.protocol !== 'https:') {
    return;
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
      // Same files and order as content_scripts in manifest.json.
      js: ['config.js', 'features.js', 'content.js'],
      runAt: 'document_start',
      persistAcrossSessions: true,
    },
  ]);
}

// A registration from an older extension version keeps its old file list, so
// it is renewed whenever the extension is installed, updated or reloaded.
chrome.runtime.onInstalled.addListener(() => {
  chrome.scripting.getRegisteredContentScripts({ ids: ['zerokey-hosted-portal'] }).then(
    (registered) => (registered.length ? registerHostedPortalScript() : undefined),
  ).catch((error) => console.error('Unable to renew the hosted portal script.', error));
});

async function unregisterHostedPortalScript() {
  const registered = await chrome.scripting.getRegisteredContentScripts({
    ids: ['zerokey-hosted-portal'],
  });
  if (registered.length) {
    await chrome.scripting.unregisterContentScripts({ ids: ['zerokey-hosted-portal'] });
  }
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

function isValidIpAddress(value) {
  const ipv4Parts = value.split('.');
  if (
    ipv4Parts.length === 4 &&
    ipv4Parts.every((part) => /^(0|[1-9]\d{0,2})$/.test(part) && Number(part) <= 255)
  ) {
    return true;
  }
  if (!value.includes(':')) {
    return false;
  }
  try {
    return new URL(`http://[${value}]/`).hostname.startsWith('[');
  } catch {
    return false;
  }
}

async function getPublicIpAddress() {
  try {
    const saved = await chrome.storage.session.get([PUBLIC_IP_KEY, PUBLIC_IP_FETCHED_AT_KEY]);
    if (
      typeof saved[PUBLIC_IP_KEY] === 'string' &&
      isValidIpAddress(saved[PUBLIC_IP_KEY]) &&
      typeof saved[PUBLIC_IP_FETCHED_AT_KEY] === 'number' &&
      Date.now() - saved[PUBLIC_IP_FETCHED_AT_KEY] < PUBLIC_IP_CACHE_TTL_MS
    ) {
      return { address: saved[PUBLIC_IP_KEY], status: 'available' };
    }
  } catch (error) {
    console.warn('Unable to read the cached public IP; requesting a fresh value.', error);
  }

  for (const provider of PUBLIC_IP_LOOKUP_PROVIDERS) {
    try {
      const response = await fetch(provider.url, {
        cache: 'no-store',
        signal: AbortSignal.timeout(5_000),
      });
      if (!response.ok) {
        throw new Error(`${provider.name} returned HTTP ${response.status}.`);
      }
      const result = await provider.readAddress(response);
      const address = typeof result === 'string' ? result.trim() : '';
      if (!isValidIpAddress(address)) {
        throw new Error(`${provider.name} returned an invalid IP address.`);
      }
      try {
        await chrome.storage.session.set({
          [PUBLIC_IP_KEY]: address,
          [PUBLIC_IP_FETCHED_AT_KEY]: Date.now(),
        });
      } catch (error) {
        console.warn(`Unable to cache the public IP returned by ${provider.name}.`, error);
      }
      return { address, status: 'available' };
    } catch (error) {
      console.warn(`Public IP lookup with ${provider.name} failed.`, error);
    }
  }

  return { address: null, status: 'lookup_failed' };
}

function tokenSubject(token) {
  try {
    const part = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const claims = JSON.parse(atob(part + '='.repeat((4 - (part.length % 4)) % 4)));
    return typeof claims.sub === 'string' ? claims.sub : null;
  } catch {
    return null;
  }
}

async function setWarningBadge(show) {
  try {
    await chrome.action.setBadgeBackgroundColor({ color: '#d93025' });
    await chrome.action.setBadgeText({ text: show ? '!' : '' });
  } catch (error) {
    console.warn('Unable to update the extension badge.', error);
  }
}

function isRetryable(error) {
  // No status: no sign-in or no network. 401/403: sign-in expired. 408/429/5xx: try later.
  const status = error?.status;
  return status === undefined || [401, 403, 408, 429].includes(status) || status >= 500;
}

async function rememberSubject(token) {
  const subject = tokenSubject(token);
  if (subject) {
    await chrome.storage.local.set({ [LAST_SUBJECT_KEY]: subject });
  }
  return subject;
}

async function queueWindow(payload) {
  const saved = await chrome.storage.local.get([
    PENDING_WINDOWS_KEY,
    LAST_SUBJECT_KEY,
    TELEMETRY_CONSENT_KEY,
  ]);
  if (saved[TELEMETRY_CONSENT_KEY] !== true || typeof saved[LAST_SUBJECT_KEY] !== 'string') {
    return false;
  }
  const now = Date.now();
  const pending = (saved[PENDING_WINDOWS_KEY] ?? []).filter(
    (item) => now - item.queued_at < MAX_PENDING_AGE_MS,
  );
  pending.push({ subject: saved[LAST_SUBJECT_KEY], queued_at: now, payload });
  await chrome.storage.local.set({ [PENDING_WINDOWS_KEY]: pending.slice(-MAX_PENDING_WINDOWS) });
  return true;
}

async function clearPendingWindows() {
  await chrome.storage.local.remove([PENDING_WINDOWS_KEY, LAST_SUBJECT_KEY]);
}

let flushInProgress = null;

function flushPendingWindows() {
  flushInProgress ??= (async () => {
    try {
      const subject = await rememberSubject(await getAccessToken());
      const saved = await chrome.storage.local.get(PENDING_WINDOWS_KEY);
      const now = Date.now();
      // Windows of another user are never sent under this sign-in.
      let pending = (saved[PENDING_WINDOWS_KEY] ?? []).filter(
        (item) => subject && item.subject === subject && now - item.queued_at < MAX_PENDING_AGE_MS,
      );
      let sent = 0;
      while (pending.length) {
        try {
          await sendTelemetry(pending[0].payload);
          sent += 1;
        } catch (error) {
          if (isRetryable(error)) {
            break;
          }
          console.error('Dropping a saved window the API rejected.', error);
        }
        pending = pending.slice(1);
        await chrome.storage.local.set({ [PENDING_WINDOWS_KEY]: pending });
      }
      await chrome.storage.local.set({ [PENDING_WINDOWS_KEY]: pending });
      return sent;
    } finally {
      flushInProgress = null;
    }
  })();
  return flushInProgress;
}

async function forwardTelemetry(payload) {
  try {
    const result = await sendTelemetry(payload);
    await setWarningBadge(false);
    flushPendingWindows().catch((error) => console.warn('Unable to send saved windows yet.', error));
    return result;
  } catch (error) {
    await setWarningBadge(true);
    if (isRetryable(error) && (await queueWindow(payload).catch(() => false))) {
      error.message += ' This window was saved and will be sent after you sign in again (refresh the portal).';
    }
    throw error;
  }
}

async function sendTelemetry(payload) {
  const consent = await chrome.storage.local.get(TELEMETRY_CONSENT_KEY);
  if (consent[TELEMETRY_CONSENT_KEY] !== true) {
    throw new Error('Telemetry consent is required before sending behavior features.');
  }
  const accessToken = await getAccessToken();
  await rememberSubject(accessToken);
  const deviceId = await getDeviceId();
  const publicIp = await getPublicIpAddress();
  const response = await fetch(TELEMETRY_API_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      ...payload,
      device_id: deviceId,
      public_ip_address: publicIp.address,
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
    const error = new Error(`Telemetry API returned HTTP ${response.status}: ${detail}`);
    error.status = response.status;
    throw error;
  }
  return { public_ip_status: publicIp.status };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const senderOrigin = sender.tab?.url ? new URL(sender.tab.url).origin : null;
  if (message?.type === 'portal-enable') {
    if (sender.tab || sender.url !== chrome.runtime.getURL('popup.html')) {
      sendResponse({ ok: false, error: 'Portal access must be enabled from the extension popup.' });
      return false;
    }
    registerHostedPortalScript().then(
      () => sendResponse({ ok: true }),
      (error) => {
        console.error('Unable to register the configured hosted portal.', error);
        sendResponse({ ok: false, error: 'Unable to enable the configured portal.' });
      },
    );
    return true;
  }

  if (message?.type === 'portal-auth') {
    if (
      !senderOrigin ||
      !ALLOWED_PORTAL_ORIGINS.has(senderOrigin) ||
      typeof message.access_token !== 'string' ||
      typeof message.expires_at !== 'number' ||
      message.expires_at <= Date.now() + 30_000
    ) {
      sendResponse({ ok: false, error: 'Invalid portal authentication message.' });
      return false;
    }
    (async () => {
      const accessCheck = await fetch(`${CONFIG.apiOrigin.replace(/\/+$/, '')}/api/auth/check`, {
        headers: { Authorization: `Bearer ${message.access_token}` },
      });
      if (!accessCheck.ok) {
        throw new Error(`The API did not approve this identity (HTTP ${accessCheck.status}).`);
      }
      await chrome.storage.session.set({
        [ACCESS_TOKEN_KEY]: message.access_token,
        [ACCESS_TOKEN_EXPIRY_KEY]: message.expires_at,
      });
      await chrome.storage.local.set({ [TELEMETRY_CONSENT_KEY]: true });
      await getDeviceId();
      await registerHostedPortalScript();
      await setWarningBadge(false);
      flushPendingWindows().catch((error) => console.warn('Unable to send saved windows yet.', error));
      sendResponse({ ok: true });
    })().catch((error) => {
      console.error('Unable to validate portal authentication for telemetry.', error);
      sendResponse({
        ok: false,
        error: error instanceof Error ? error.message : 'Portal authentication failed.',
      });
    });
    return true;
  }

  if (message?.type === 'portal-consent') {
    if (!senderOrigin || !ALLOWED_PORTAL_ORIGINS.has(senderOrigin) || message.consent !== false) {
      sendResponse({ ok: false, error: 'Invalid telemetry consent message.' });
      return false;
    }
    chrome.storage.local.set({ [TELEMETRY_CONSENT_KEY]: false }).then(clearPendingWindows).then(
      () => chrome.storage.session.remove([ACCESS_TOKEN_KEY, ACCESS_TOKEN_EXPIRY_KEY]).then(
        () => sendResponse({ ok: true }),
        (error) => {
          console.error('Unable to clear portal telemetry credentials.', error);
          sendResponse({ ok: false, error: 'Consent withdrawn, but sign-in cleanup failed.' });
        },
      ),
      (error) => {
        console.error('Unable to save telemetry consent withdrawal.', error);
        sendResponse({ ok: false, error: 'Unable to save the consent choice.' });
      },
    );
    return true;
  }

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
    chrome.storage.session.remove([ACCESS_TOKEN_KEY, ACCESS_TOKEN_EXPIRY_KEY]).then(clearPendingWindows).then(
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
    chrome.storage.local.get(TELEMETRY_CONSENT_KEY).then((consent) => {
      if (consent[TELEMETRY_CONSENT_KEY] !== true) {
        throw new Error('Opt in to telemetry from the portal before collecting activity.');
      }
      return getAccessToken();
    }).then(
      () => {
        setWarningBadge(false);
        flushPendingWindows().catch((error) => console.warn('Unable to send saved windows yet.', error));
        sendResponse({ ok: true });
      },
      (error) => {
        setWarningBadge(true);
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
      (result) => sendResponse({ ok: true, ...result }),
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
