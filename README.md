# zerokey
[![CI](https://github.com/aleeshaishtiaq/zerokey/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/aleeshaishtiaq/zerokey/actions/workflows/ci.yml)

ZEROKEY - Zero Dependency Browser Extension for Continuous Post-Login Authentication and Active Cyber Deception

## Continuous Integration (CI)

The GitHub Actions workflow `.github/workflows/ci.yml` runs on every push to
`main` or `develop`, and on every pull request targeting `main` or `develop`.
The **Lint and test** job sets up Python 3.11, installs `requirements.txt`,
Flake8, and pytest, lints `src/` and `tests/`, then runs the tests in `tests/`.
The **Build frontends and check required files** job installs the locked Node
dependencies and runs the production build for both `frontend/` and
`dashboard/`. It also verifies that `frontend/index.html`,
`extension/manifest.json`, `src/api/main.py`, and the `dashboard/` directory
with at least one file exist. Build, lint, or test failures fail the workflow.

To verify a run, push a commit to `main` or `develop` or open a pull request
targeting one of those branches, then check the repository's **Actions** tab
for a green CI run. CI does not publish an artifact or deploy the application.

## Staging authentication and deployment status

The code supports Auth0 authentication, but no Auth0 tenant/application, approved
users, or Render services have been configured. Access to telemetry data fails
closed until the API has an Auth0 domain, API audience, and at least one
team-approved Auth0 subject ID in `AUTH0_ALLOWED_SUBJECTS`. The frontends check
authorization through the API; the API independently verifies the signed
access token and enforces its subject allowlist. No approved subject IDs are
embedded in public frontend bundles. Do not enable public registration or add
users until the team has approved their identities.

Use the Auth0 **default tenant domain** (no custom Auth0 domain). The intended
Auth0 setup is:

1. Create an Auth0 API with an identifier used as the audience; use RS256
   access tokens.
2. Create a Single Page Application for the portal and dashboard, and a
   separate Native Application for the Chromium extension. Do not create or add
   user accounts as part of repository setup.
3. Disable public sign-ups on the Auth0 database connection. Add only the
   approved callback URLs/origins after Render has assigned the static sites
   and the installed extension has a stable ID.
4. Configure the exact approved Auth0 `sub` values in the API environment
   allowlist. An empty allowlist deliberately denies all authenticated data
   access.

Auth0 callback and origin settings required later:

| Auth0 setting | Value to add after service setup |
|---|---|
| SPA Allowed Callback URLs | `https://<portal-service>.onrender.com/`, `https://<dashboard-service>.onrender.com/`; for local development, `http://localhost:5500/` and `http://localhost:5173/` |
| SPA Allowed Logout URLs | Both static-site URLs above |
| SPA Allowed Web Origins | Both static-site origins, without trailing slashes; add the two local origins when using localhost |
| Native Allowed Callback URLs | `chrome.identity.getRedirectURL()` for the installed extension, typically `https://<extension-id>.chromiumapp.org/` |
| API audience | The exact API identifier created in Auth0; use it in both static-site and extension configuration |

No client secret is used by the static sites or extension. Their Auth0 domain,
client IDs, audience, and API URL are public build/runtime configuration, not
secrets. Required environment names:

| Component | Required configuration |
|---|---|
| FastAPI | `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_ALLOWED_SUBJECTS`, `CORS_ALLOWED_ORIGINS`, `TELEMETRY_LOG_PATH`; Render supplies `PORT` |
| Portal static-site build | `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE`, `VITE_API_BASE_URL` |
| Dashboard static-site build | The same four `VITE_*` settings as the portal |
| Extension | `auth0Domain`, `auth0ClientId`, `auth0Audience`, `apiOrigin`, and `portalOrigin` in `extension/config.js`; the extension requests optional permissions for only those configured origins |

Do not place secrets, real telemetry logs, or approved user lists in the
repository. The API allowlist is set in Render environment configuration and
is never embedded in frontend bundles. Keep the local example files empty
until Auth0 settings and identities are approved.

The intended Render layout is a static portal (`frontend/dist`), a static
dashboard (`dashboard/dist`), and a FastAPI Web Service. The API writes JSONL
under `TELEMETRY_LOG_PATH`, which must be on a persistent disk mounted at
`/var/data`; set the path to `/var/data/telemetry_log.jsonl`. Render's `PORT`
is supplied by the platform. The API start command is
`python -m uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`, with
`/api/health` as its health-check path. Both static sites use `npm ci &&
npm run build` and publish their component's `dist` directory. The API needs a
paid Web Service and persistent disk for this durable-storage design. **No
resources have been provisioned, and live deployment is not configured.**

Once services are created, link each service to `develop` and set Render
**Auto-Deploy** to **After CI Checks Pass**. Render then waits for GitHub checks
on that same commit before deploying; PR code is not deployed because the
services track only `develop`. The existing CI workflow builds both frontends
and runs backend lint/tests. There is no independent deployment workflow that
could bypass those checks. This setting is a manual Render configuration and
must be verified on each service; it is not active yet.

## Local behavioral telemetry POC

The standalone Chromium extension collects behavior only on the explicitly
allowed local portal origins `http://localhost:5500` and
`http://127.0.0.1:5500`. Although Chromium's static match patterns cannot
restrict a port, the content script and service worker enforce these exact
origins. For staging, set the exact Render portal and API origins in
`extension/config.js`; the extension requests runtime host permission only for
those configured origins and dynamically registers its content script only on
the configured portal.

The extension records nothing until mouse or keyboard activity occurs and sends
15-second feature summaries only for windows containing activity. It does not
collect typed text, key values, names, or email addresses. Keyboard pause,
press-to-press, release-to-press, dwell-time, typing-rate, and rollover
aggregates are computed locally; long idle gaps are excluded from latency and
typing-rate calculations.

### Install and run the backend

From the repository root, create and activate a virtual environment, then install
the backend dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:AUTH0_DOMAIN = ""
$env:AUTH0_AUDIENCE = ""
$env:AUTH0_ALLOWED_SUBJECTS = ""
$env:CORS_ALLOWED_ORIGINS = ""
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8765
```

Local API configuration is supplied through PowerShell environment variables.
Set `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, `AUTH0_ALLOWED_SUBJECTS`, and
`CORS_ALLOWED_ORIGINS` in that terminal before starting Uvicorn. Keep
`AUTH0_ALLOWED_SUBJECTS` empty until the team approves identities; with it
empty, telemetry write/read requests deliberately return HTTP 503. The
`/api/health` route remains available. The Vite apps read their settings from
`frontend/.env.local` and `dashboard/.env.local`; copy each component's
`.env.example` and keep all approved-subject values out of Git.

For local Auth0 testing later, add `http://localhost:5500/` and
`http://localhost:5173/` to the SPA callback/logout settings and their origins
to Allowed Web Origins. The extension's exact `chrome-extension://` origin
must also be added to `CORS_ALLOWED_ORIGINS` after the unpacked extension ID is
known.

The API exposes public `GET /api/health` and Auth0-protected
`GET /api/auth/check`, `POST /api/telemetry`, and
`GET /api/telemetry/recent`. Protected routes validate Auth0 RS256 access
tokens and require an exact allowlisted subject. Until
`AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, and `AUTH0_ALLOWED_SUBJECTS` are configured,
data access is denied. CORS is limited to the explicit configured origins (or
localhost development defaults) and does not replace token authentication.
The extension looks up the visitor's public IP using ipify's free
`https://api.ipify.org?format=json`
endpoint only after a behavioral activity window is ready to send, and caches
the result in session-only extension storage for 15 minutes. ipify therefore
receives the visitor's public IP; this is a public egress address, which can
belong to a VPN, proxy, or shared network and is not necessarily a unique user
or their local network address. If the lookup fails, feature data is still
saved with a `null` public IP.

### Run the portal and dashboard

The portal and dashboard are Vite applications now. After configuring the
Auth0 values and an approved subject in ignored local `.env` files, run the
portal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://localhost:5500`. In another terminal, run the admin dashboard:

```powershell
cd dashboard
npm ci
npm run dev
```

Open the Vite URL (usually `http://localhost:5173`) and select **Telemetry**.
Both frontends intentionally deny access when Auth0 settings are missing or
the API has no approved subject allowlist.

### Load and verify the extension

1. Open `chrome://extensions`, enable **Developer mode**, select **Load
   unpacked**, and choose the repository's `extension/` folder. If the
   extension is already installed, click its **Reload** button after changing
   extension files.
2. Keep the FastAPI server running, open the enterprise portal, and sign in
   with an approved Auth0 identity. Sign in separately from the extension
   popup. Open **Complaints & requests**, choose **Create ticket**, and type a fictional issue in the
   **Complaint description** field, or move/click the mouse. After an active
   15-second window, feature values are sent to the API using the extension's
   Auth0 token. The complaint form shows collector status. Typed characters
   are never stored or sent.
3. The extension popup reports whether the configured API is reachable. The
   dashboard's **Telemetry** page refreshes every five seconds; use its
   **Refresh** button to fetch immediately.
4. The dashboard retrieves recent records with its Auth0 access token.

### Where telemetry is stored and troubleshooting

The backend appends one JSON object per line to
`data/raw/zerokey_captured/telemetry_log.jsonl` in the repository. On this
Windows checkout, the path is
`<repository>\data\raw\zerokey_captured\telemetry_log.jsonl`. This is the
durable copy; records are not stored in the portal or dashboard.
The **Telemetry** dashboard reads the latest 50 current-format entries from the API.
Older entries from before this collector fix are intentionally excluded from
the dashboard and `/api/telemetry/recent`; they remain in the JSONL archive.
The log is ignored by Git.

If no new row appears, check that the portal URL is exactly
`http://localhost:5500` or `http://127.0.0.1:5500`, all Auth0 settings and
allowlists match, the extension is signed in, and the API is running. Reload
the extension from `chrome://extensions` and reload the portal tab. Then open
**Complaints & requests** > **Create ticket**, type a few
fictional characters in **Complaint description**, then wait up to 15 seconds.
Check `http://127.0.0.1:8765/api/health` for backend status. Recent-record
requests require an approved Auth0 bearer token. A blocked
ipify lookup no longer prevents behavior from being saved; that record's
`public_ip_address` will be `null`.
If the extension reports HTTP 422, reload the extension and portal after
updating them; the collector status now includes the API's rejected field and
validation message.

Each record contains a SHA-256 device identifier, a per-tab session UUID
(renewed after 30 minutes of inactivity), an ISO timestamp, a public IP from
ipify when available, and only the shortlisted mouse and keyboard aggregates.
The extension emits aggregate features rather than transmitting typed text,
raw event rows, coordinates, or key values.
