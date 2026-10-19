const status = document.getElementById('status');
const authStatus = document.getElementById('auth-status');
const CONFIG = globalThis.ZERO_KEY_CONFIG;
const redirectUri = chrome.identity.getRedirectURL();
document.getElementById('redirect-uri').textContent = redirectUri;

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

document.getElementById('sign-in').addEventListener('click', async () => {
  try {
    if (!/^[A-Za-z0-9.-]+\.auth0\.com$/.test(CONFIG.auth0Domain) ||
        !CONFIG.auth0ClientId ||
        !CONFIG.auth0Audience) {
      throw new Error('Configure the Auth0 tenant, extension client ID, and API audience first.');
    }

    const origins = [`https://${CONFIG.auth0Domain}/*`];
    for (const configuredOrigin of [CONFIG.apiOrigin, CONFIG.portalOrigin]) {
      const parsedOrigin = new URL(configuredOrigin);
      if (parsedOrigin.protocol === 'https:') {
        origins.push(`${parsedOrigin.origin}/*`);
      }
    }
    const granted = await chrome.permissions.request({ origins });
    if (!granted) {
      throw new Error('The required exact portal, API, and Auth0 host permissions were not granted.');
    }

    const result = await chrome.runtime.sendMessage({ type: 'auth-login' });
    if (!result?.ok) {
      throw new Error(result?.error || 'Auth0 sign-in failed.');
    }
    authStatus.textContent = 'Signed in. Reload the configured portal to enable collection.';
  } catch (error) {
    console.error('Extension sign-in failed.', error);
    const message = error instanceof Error ? error.message : 'Extension sign-in failed.';
    authStatus.textContent = message === 'Authorization page could not be loaded.'
      ? `Auth0 could not complete sign-in. Check that the callback URL above is in the ZeroKey Extension Native app's Allowed Callback URLs, and that the app is authorized for ZeroKey API.`
      : message;
  }
});

document.getElementById('sign-out').addEventListener('click', async () => {
  const result = await chrome.runtime.sendMessage({ type: 'auth-logout' });
  authStatus.textContent = result?.ok ? 'Signed out.' : result?.error || 'Sign-out failed.';
});
