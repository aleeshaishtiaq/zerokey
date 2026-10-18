const status = document.getElementById('status');

fetch('http://127.0.0.1:8765/api/health')
  .then((response) => {
    if (!response.ok) {
      throw new Error(`Health check returned HTTP ${response.status}.`);
    }
    return response.json();
  })
  .then((result) => {
    status.textContent = result.status === 'ok' ? 'Local telemetry API is reachable.' : 'Unexpected API health response.';
  })
  .catch((error) => {
    console.error('Unable to reach the local ZeroKey API.', error);
    status.textContent = 'Local telemetry API is unavailable.';
  });
