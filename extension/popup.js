const status = document.getElementById('status');
const authStatus = document.getElementById('auth-status');
const CONFIG = globalThis.ZERO_KEY_CONFIG;

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

document.getElementById('sign-out').addEventListener('click', async () => {
  const result = await chrome.runtime.sendMessage({ type: 'auth-logout' });
  authStatus.textContent = result?.ok ? 'Signed out.' : result?.error || 'Sign-out failed.';
});
