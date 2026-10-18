const DEVICE_ID_KEY = 'device_id';
const TELEMETRY_API_URL = 'http://127.0.0.1:8765/api/telemetry';
const PUBLIC_IP_CACHE_KEY = 'public_ip_cache';
const PUBLIC_IP_CACHE_DURATION_MS = 15 * 60 * 1000;
const ALLOWED_PORTAL_ORIGINS = new Set([
  'http://localhost:5500',
  'http://127.0.0.1:5500',
]);

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
  let publicIpAddress = null;
  try {
    publicIpAddress = await getPublicIpAddress();
  } catch (error) {
    console.warn('Public IP lookup failed; sending behavioral features without an IP.', error);
  }

  const deviceId = await getDeviceId();
  const response = await fetch(TELEMETRY_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...payload,
      device_id: deviceId,
      public_ip_address: publicIpAddress,
    }),
  });

  if (!response.ok) {
    const detail = await response.text();
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
        console.error('Unable to send behavioral telemetry to the local API.', error);
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
