// Runs the real extension/background.js with a fake chrome API and prints
// what happened in a few delivery scenarios. Used by tests/test_extension_queue.py.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const PORTAL = 'https://portal.test';
const posted = [];
let apiStatus = 200;
let listener = null;
let badge = '';

function area() {
  const data = new Map();
  return {
    data,
    get: async (keys) => {
      const list = Array.isArray(keys) ? keys : [keys];
      return Object.fromEntries(list.filter((key) => data.has(key)).map((key) => [key, data.get(key)]));
    },
    set: async (items) => { for (const [key, value] of Object.entries(items)) data.set(key, value); },
    remove: async (keys) => { for (const key of [].concat(keys)) data.delete(key); },
  };
}
const local = area();
const session = area();

function token(sub) {
  const part = Buffer.from(JSON.stringify({ sub })).toString('base64url');
  return `header.${part}.signature`;
}

const sandbox = {
  console: { ...console, error() {}, warn() {} },
  crypto: require('crypto').webcrypto,
  atob, btoa, URL, AbortSignal, TextEncoder, TextDecoder,
  importScripts() {
    sandbox.ZERO_KEY_CONFIG = {
      apiOrigin: 'https://api.test', portalOrigin: PORTAL,
      auth0Domain: 'x.auth0.com', auth0ClientId: 'id', auth0Audience: 'aud',
    };
  },
  fetch: async (url, options = {}) => {
    if (String(url).includes('ipify')) return { ok: true, json: async () => ({ ip: '1.2.3.4' }) };
    if (String(url).endsWith('/api/auth/check')) return { ok: true };
    posted.push(JSON.parse(options.body));
    return { ok: apiStatus < 400, status: apiStatus, text: async () => '{"detail":"x"}' };
  },
  chrome: {
    storage: { local, session },
    runtime: { onMessage: { addListener: (fn) => { listener = fn; } }, onInstalled: { addListener() {} }, getURL: (p) => `chrome-extension://id/${p}` },
    action: { setBadgeText: async ({ text }) => { badge = text; }, setBadgeBackgroundColor: async () => {} },
    permissions: { contains: async () => false },
    scripting: {
      getRegisteredContentScripts: async () => [],
      registerContentScripts: async () => {},
      unregisterContentScripts: async () => {},
    },
  },
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'extension', 'background.js'), 'utf8'), sandbox);

function send(message, sender = { tab: { url: `${PORTAL}/` } }) {
  return new Promise((resolve) => { listener(message, sender, resolve); });
}
const tick = () => new Promise((resolve) => setTimeout(resolve, 20));
const windowPayload = (n) => ({ collection_version: 2, session_id: 's', timestamp: `t${n}`, mouse_features: {}, keyboard_features: {} });
const signIn = (sub) => send({ type: 'portal-auth', access_token: token(sub), expires_at: Date.now() + 3_600_000 });
const signOutToken = () => session.remove(['auth0_access_token', 'auth0_access_token_expiry']);

(async () => {
  const result = {};
  await signIn('user-a');
  await send({ type: 'telemetry-window', payload: windowPayload(1) });
  result.first_sent = posted.map((p) => p.timestamp);

  await signOutToken();                                  // sign-in expired
  const failed = await send({ type: 'telemetry-window', payload: windowPayload(2) });
  await send({ type: 'telemetry-window', payload: windowPayload(3) });
  result.failed_message_mentions_saved = /saved/.test(failed.error);
  result.badge_after_failure = badge;
  result.queued = (local.data.get('pending_windows') ?? []).map((item) => item.payload.timestamp);

  await signIn('user-a');                                // same user signs in again
  await tick();
  result.sent_after_same_user = posted.map((p) => p.timestamp);
  result.badge_after_sign_in = badge;

  await signOutToken();
  await send({ type: 'telemetry-window', payload: windowPayload(4) });
  await signIn('user-b');                                // another user on the same browser
  await tick();
  result.sent_after_other_user = posted.map((p) => p.timestamp);
  result.queue_after_other_user = (local.data.get('pending_windows') ?? []).length;

  apiStatus = 422;                                       // rejected data is not saved
  await send({ type: 'telemetry-window', payload: windowPayload(5) });
  result.queue_after_422 = (local.data.get('pending_windows') ?? []).length;
  apiStatus = 200;

  await signOutToken();
  await send({ type: 'telemetry-window', payload: windowPayload(6) });
  result.queue_before_logout = (local.data.get('pending_windows') ?? []).length;
  await send({ type: 'auth-logout' }, { url: 'chrome-extension://id/popup.html' });
  result.queue_after_logout = (local.data.get('pending_windows') ?? []).length;

  process.stdout.write(JSON.stringify(result));
})();
