const status = document.getElementById('status');
const authStatus = document.getElementById('auth-status');
const publicIpButton = document.getElementById('enable-public-ip');
const CONFIG = globalThis.ZERO_KEY_CONFIG;
const PUBLIC_IP_ENABLED_KEY = 'public_ip_lookup_enabled';
const PUBLIC_IP_CACHE_KEYS = ['public_ip_address', 'public_ip_fetched_at'];

function updatePublicIpButton(enabled) {
  publicIpButton.textContent = enabled
    ? 'Disable public IP lookup (ipify)'
    : 'Enable public IP lookup (ipify)';
}

chrome.storage.local.get(PUBLIC_IP_ENABLED_KEY).then(
  (settings) => updatePublicIpButton(settings[PUBLIC_IP_ENABLED_KEY] === true),
  (error) => {
    console.error('Unable to read the public IP lookup setting.', error);
    authStatus.textContent = 'Unable to read the public IP lookup setting.';
  },
);

fetch(`${CONFIG.apiOrigin.replace(/\/+$/, '')}/api/health`)
  .then((response) => {
    if (!response.ok) {
      throw new Error(`Health check returned HTTP ${response.status}.`);
    }
    return response.json();
  })
  .then((result) => {
    status.textContent = result.status === 'ok' ? 'Configured telemetry API is reachable.' : 'Unexpected API health response.';
  })
  .catch((error) => {
    console.error('Unable to reach the configured ZeroKey API.', error);
    status.textContent = 'Configured telemetry API is unavailable.';
  });

document.getElementById('enable-portal').addEventListener('click', async () => {
  try {
   const apiOrigin = new URL(CONFIG.apiOrigin).origin;
   const portalOrigin = new URL(CONFIG.portalOrigin).origin;
   if (!['http:', 'https:'].includes(new URL(CONFIG.portalOrigin).protocol)) {
     throw new Error('Configure the portal URL before enabling this integration.');
    }
   const origins = [`${apiOrigin}/*`, `${portalOrigin}/*`];
    const granted = await chrome.permissions.request({ origins });
    if (!granted) {
     throw new Error('The exact configured portal and API permissions were not granted.');
    }

   const result = await chrome.runtime.sendMessage({ type: 'portal-enable' });
    if (!result?.ok) {
     throw new Error(result?.error || 'Portal integration could not be enabled.');
    }
   authStatus.textContent = 'Portal access enabled. Reload it, sign in with Auth0, and choose whether to opt in.';
  } catch (error) {
   console.error('Portal integration could not be enabled.', error);
   authStatus.textContent = error instanceof Error ? error.message : 'Portal integration could not be enabled.';
  }
});

publicIpButton.addEventListener('click', async () => {
  try {
    const settings = await chrome.storage.local.get(PUBLIC_IP_ENABLED_KEY);
    const enabled = settings[PUBLIC_IP_ENABLED_KEY] !== true;
    await chrome.storage.local.set({ [PUBLIC_IP_ENABLED_KEY]: enabled });
    if (!enabled) {
      await chrome.storage.session.remove(PUBLIC_IP_CACHE_KEYS);
    }
    updatePublicIpButton(enabled);
    authStatus.textContent = enabled
      ? 'Public IP lookup enabled. ipify will be contacted only when opted-in telemetry is sent.'
      : 'Public IP lookup disabled. No public IP will be sent.';
  } catch (error) {
    console.error('Unable to update the public IP lookup setting.', error);
    authStatus.textContent = error instanceof Error
      ? error.message
      : 'Unable to update the public IP lookup setting.';
  }
});

document.getElementById('sign-out').addEventListener('click', async () => {
  const result = await chrome.runtime.sendMessage({ type: 'auth-logout' });
  authStatus.textContent = result?.ok ? 'Signed out.' : result?.error || 'Sign-out failed.';
});
