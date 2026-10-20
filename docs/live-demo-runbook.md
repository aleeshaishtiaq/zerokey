# ZeroKey Live Demo Runbook

This runbook covers the localhost flow:

```text
portal activity -> Chrome extension -> authenticated API POST
-> FastAPI validation and JSONL storage -> dashboard GET -> dashboard UI
```

No Auth0 Management API secret, client secret, bearer token, Vercel token, or
private key belongs in this repository.

## Configuration

The code reads `VITE_API_URL` for both Vite applications. It does not read
`VITE_API_BASE_URL`. The local target is `http://127.0.0.1:8765`.

Create ignored local files from the examples, without committing them:

```powershell
Copy-Item .env.example .env.local
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item dashboard/.env.example dashboard/.env.local
```

Set the real approved values only in local environment files. The backend
requires `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_ALLOWED_SUBJECTS`,
`CORS_ALLOWED_ORIGINS`, and optionally `TELEMETRY_LOG_PATH`.

The portal and dashboard require `VITE_AUTH0_DOMAIN`, their own SPA client ID,
`VITE_AUTH0_AUDIENCE`, and `VITE_API_URL`. The extension requires its Native
Application client ID in `extension/config.js`; replace the placeholder locally
only. The portal SPA client ID must not be used in the extension.

## Auth0 checklist

Create/configure these application types manually:

- ZeroKey Portal Dashboard: Single Page Application
- ZeroKey Extension: Native Application
- ZeroKey API: API/resource server, audience `https://zerokey-fyp-api`

Portal SPA callback/logout/Web Origins:

```text
http://localhost:5500/
http://127.0.0.1:5500/
http://localhost:5500
http://127.0.0.1:5500
```

Dashboard SPA callback/logout/Web Origins:

```text
http://localhost:5173/
http://127.0.0.1:5173/
http://localhost:5173
http://127.0.0.1:5173
```

The extension Native Application callback is the value printed by
`chrome.identity.getRedirectURL()` in its popup. Do not add a client secret to
the extension.

`AUTH0_ALLOWED_SUBJECTS` is an authorization allowlist, not authentication.
Each teammate must use an approved Auth0 subject or the API returns `403`.

## Start locally

Use four terminals. No server is started by this document.

Terminal 1, repository root:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8765
```

Terminal 2, `frontend`:

```powershell
npm ci
npm run dev
```

Open `http://127.0.0.1:5500`.

Terminal 3, `dashboard`:

```powershell
npm ci
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

The extension is loaded separately:

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Choose **Load unpacked** and select `extension/`.
4. Copy the generated extension ID.
5. Put `chrome-extension://<extension-id>` in backend `CORS_ALLOWED_ORIGINS`.
6. Reload the extension and restart the backend after changing CORS.
7. Open the extension popup and grant requested permissions.
8. Sign in through the extension popup.

## Live verification

1. Check `http://127.0.0.1:8765/api/health`; expect `{"status":"ok"}`.
2. Sign in to the portal with an approved identity.
3. Open **Complaints & requests** and choose **Create demo ticket**.
4. Enter harmless fictional text such as `demo activity`.
5. Move the mouse and click in the portal.
6. Wait approximately 15 seconds for the feature window to batch.
7. In the extension service-worker DevTools, inspect a `POST /api/telemetry`
   request and `201` response. Hide Authorization, device ID, IP, and payload
   values in screenshots.
8. In the Uvicorn terminal, confirm the POST was received.
9. Inspect `data/raw/zerokey_captured/telemetry_log.jsonl` locally. Do not
   paste the full record into chat or presentation material.
10. In dashboard DevTools, inspect `GET /api/telemetry/recent?limit=50` with
    status `200`.
11. Open dashboard **Telemetry**. It polls every five seconds and also has a
    Refresh button.

Correlate the stages using timestamp and a redacted session UUID suffix. Do
not show full session IDs, device hashes, IP addresses, bearer tokens, or
Auth0 credentials.

The backend routes are:

```text
GET  /api/health
GET  /api/auth/check
POST /api/telemetry
GET  /api/telemetry/recent?limit=50
```

FastAPI documentation defaults are expected at `/docs`, `/redoc`, and
`/openapi.json`; these URLs are not enabled by a custom application setting.

## Failure diagnosis

| Symptom | Inspect |
| --- | --- |
| Popup says API unreachable | Backend process, `extension/config.js`, `/api/health` |
| Auth0 redirect fails | Auth0 callback URL, SPA/Native application type, audience |
| `401` from POST | Bearer token acquisition and expiry |
| `403` from POST | `AUTH0_ALLOWED_SUBJECTS` does not contain the token subject |
| CORS error | Exact extension origin in `CORS_ALLOWED_ORIGINS` and API target |
| Backend receives but dashboard is empty | Dashboard `VITE_API_URL`, dashboard Auth0 check, Network response |
| Dashboard shows mock data | Use the Telemetry route; other dashboard pages use local/mock data |
| Vercel health works but local flow fails | Local clients still point to `127.0.0.1:8765`; verify both targets separately |

## Teammate setup

```powershell
git clone <repository-url>
cd zerokey
Copy-Item .env.example .env.local
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item dashboard/.env.example dashboard/.env.local
python -m pip install -r requirements.txt
cd frontend; npm ci; cd ..
cd dashboard; npm ci; cd ..
```

Each teammate needs an approved Auth0 subject, their local extension ID in
backend CORS, and the extension Native Application client ID. They must never
share tokens, client secrets, private keys, or telemetry logs.

## Scope boundary

The live telemetry path is implemented, but it requires local Auth0/CORS
configuration and has not been live-verified by this repository task. The
keystroke pipeline is preprocessing only; it is not model training, risk
scoring, or continuous learning.