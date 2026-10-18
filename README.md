# zerokey
[![CI](https://github.com/aleeshaishtiaq/zerokey/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aleeshaishtiaq/zerokey/actions/workflows/ci.yml)

ZEROKEY - Zero Dependency Browser Extension for Continuous Post-Login Authentication and Active Cyber Deception

## CI pipeline

GitHub Actions runs on every push to `main` or `develop` and on pull requests
targeting either branch. The **Lint and test** job uses Python 3.11, installs
the backend requirements plus Flake8 and pytest, lints `src/` and `tests/`,
then runs the Python test suite. The **Check required project files** job
verifies the portal, extension manifest, API entry point, and dashboard files
are present. A lint error or failed test fails its job.

To verify a run, push a commit to `main` or `develop` or open a pull request
targeting one of those branches, then check the repository's **Actions** tab
for a green CI run.

## Local behavioral telemetry POC

The standalone Chromium extension collects behavior only on the explicitly
allowed local portal origins `http://localhost:5500` and
`http://127.0.0.1:5500`. Although Chromium's match patterns cannot restrict a
port, the content script and service worker both enforce these exact origins;
all other pages, including other localhost ports and Vercel sites, are ignored.
No production portal domain is currently configured. Add its exact origin to
both allowlists in `extension/content.js` and `extension/background.js`, and a
matching host pattern to `extension/manifest.json`, before deployment.

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
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8765
```

The API exposes `GET /api/health`, `POST /api/telemetry`, and
`GET /api/telemetry/recent`. CORS is enabled without credentials for Chrome
extension origins and localhost dashboard origins. The extension looks up the
visitor's public IP using ipify's free `https://api.ipify.org?format=json`
endpoint only after a behavioral activity window is ready to send, and caches
the result in session-only extension storage for 15 minutes. ipify therefore
receives the visitor's public IP; this is a public egress address, which can
belong to a VPN, proxy, or shared network and is not necessarily a unique user
or their local network address. If the lookup fails, feature data is still
saved with a `null` public IP.

### Run the portal and dashboard

In a separate terminal, serve the existing static enterprise portal without
changing its files:

```powershell
cd frontend
py -m http.server 5500
```

Open `http://localhost:5500` (or `http://127.0.0.1:5500`). In another
terminal, run the existing admin dashboard:

```powershell
cd dashboard
npm install
npm run dev
```

Open the Vite URL (usually `http://localhost:5173`) and select **Telemetry** in
the sidebar. This is a separate page; existing dashboard pages are unchanged.

### Load and verify the extension

1. Open `chrome://extensions`, enable **Developer mode**, select **Load
   unpacked**, and choose the repository's `extension/` folder. If the
   extension is already installed, click its **Reload** button after changing
   extension files.
2. Keep the FastAPI server running, open or reload the enterprise portal, and
   sign in with the demo credentials shown on the page. Open **Complaints &
   requests**, choose **Create ticket**, and type a fictional issue in the
   **Complaint description** field, or move/click the mouse. After an active
   15-second window, feature values are sent to the API. The complaint form
   shows collector status so delivery errors are visible. Typed characters
   are never stored or sent.
3. The extension popup reports whether the local API is reachable. The
   dashboard's **Telemetry** page refreshes every five seconds; use its
   **Refresh** button to fetch immediately.
4. `GET http://127.0.0.1:8765/api/telemetry/recent` returns the latest records
   from the saved log, including after the backend is restarted.

### Where telemetry is stored and troubleshooting

The backend appends one JSON object per line to
`data/raw/zerokey_captured/telemetry_log.jsonl` in the repository. On this
Windows checkout, the file is
`C:\Users\azka nadeem\Documents\zerokey\data\raw\zerokey_captured\telemetry_log.jsonl`.
This is the durable copy; records are not stored in the portal or dashboard.
The **Telemetry** dashboard reads the latest 50 current-format entries from the API.
Older entries from before this collector fix are intentionally excluded from
the dashboard and `/api/telemetry/recent`; they remain in the JSONL archive.
The log is ignored by Git.

If no new row appears, check that the portal URL is exactly
`http://localhost:5500` or `http://127.0.0.1:5500`, reload the extension from
`chrome://extensions`, reload the portal tab, and keep the backend running.
Sign in, open **Complaints & requests** > **Create ticket**, type a few
fictional characters in **Complaint description**, then wait up to 15 seconds.
Check `http://127.0.0.1:8765/api/health` for backend status and
`http://127.0.0.1:8765/api/telemetry/recent` for saved records. A blocked
ipify lookup no longer prevents behavior from being saved; that record's
`public_ip_address` will be `null`.

Each record contains a SHA-256 device identifier, a per-tab session UUID
(renewed after 30 minutes of inactivity), an ISO timestamp, a public IP from
ipify when available, and only the shortlisted mouse and keyboard aggregates.
The extension emits aggregate features rather than transmitting typed text,
raw event rows, coordinates, or key values.
