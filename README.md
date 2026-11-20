# zerokey
[![CI](https://github.com/aleeshaishtiaq/zerokey/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/aleeshaishtiaq/zerokey/actions/workflows/ci.yml)

ZEROKEY - Zero Dependency Browser Extension for Continuous Post-Login Authentication and Active Cyber Deception

## Continuous Integration (CI)

The GitHub Actions workflow `.github/workflows/ci.yml` runs on every push to
`main` or `develop`, and on every pull request targeting `main` or `develop`.
The **Lint and test** job sets up Python from the checked-out branch's
`.python-version` file (currently Python 3.12 on `main` and 3.14 on `develop`),
installs `requirements.txt`, Flake8, and pytest, lints `src/` and `tests/`, then
runs the tests in `tests/`.
The **Build frontends and check required files** job installs the locked Node
dependencies and runs the production build for both `frontend/` and
`dashboard/`. It also verifies that `frontend/index.html`,
`extension/manifest.json`, `src/api/main.py`, and the `dashboard/` directory
with at least one file exist. Build, lint, or test failures fail the workflow.

To verify a run, push a commit to `main` or `develop` or open a pull request
targeting one of those branches, then check the repository's **Actions** tab
for a green CI run. The separate CD workflow deploys only the FastAPI API to
Vercel after a successful `develop` push; it does not deploy the enterprise
portal.

## Enterprise portal Vercel deployment

The enterprise portal is `frontend/`, not the project currently served at
`https://zerokey.vercel.app`. That URL redirects to
`https://zerokey.dippan.com.np/`, an unrelated encrypted-messaging site, so the
enterprise portal is not verified as deployed on Vercel.

Create a separate Vercel project for this portal with `frontend/` as its root
directory, the Vite framework preset, `npm ci` as the install command,
`npm run build` as the build command, and `dist` as the output directory.
`frontend/vercel.json` provides the SPA fallback for client-side routes. Set
`VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE`, and
`VITE_API_URL` in the Vercel project before enabling sign-in. Do not reuse the
existing `zerokey.vercel.app` alias for this unrelated project.

The API also needs a production URL and approved Auth0 subject allowlist before
the portal can collect live telemetry.

## Staging authentication and deployment status

Access to telemetry data fails closed until the API has an Auth0 domain, API
audience, and at least one team-approved Auth0 subject ID in
`AUTH0_ALLOWED_SUBJECTS`. The frontends check authorization through the API;
the API independently verifies the signed access token and enforces its
subject allowlist. No approved subject IDs are embedded in public frontend
bundles. Do not enable public registration or add users until the team has
approved their identities.

Use the Auth0 **default tenant domain** (no custom Auth0 domain). The intended
Auth0 setup is:

1. Create an Auth0 API with an identifier used as the audience; use RS256
   access tokens.
2. Create a Single Page Application for the portal and dashboard, and a
   separate Native Application for the Chromium extension. Do not create or add
   user accounts as part of repository setup.
3. Disable public sign-ups on the Auth0 database connection. Add only the
   approved callback URLs/origins after Vercel has assigned the portal URL,
   the API URL is ready, and the installed extension has a stable ID.
4. Configure the exact approved Auth0 `sub` values in the API environment
   allowlist. An empty allowlist deliberately denies all authenticated data
   access.

Auth0 callback and origin settings required later:

| Auth0 setting | Value to add after service setup |
|---|---|
| SPA Allowed Callback URLs | `https://<enterprise-portal>.vercel.app/`, `https://<dashboard-service>.onrender.com/`; for local development, `http://127.0.0.1:5500/`, `http://localhost:5500/`, and `http://localhost:5173/` |
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
| Portal static-site build | `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE`, `VITE_API_URL` |
| Dashboard static-site build | The same four `VITE_*` settings as the portal |
| Extension | `auth0Domain`, `auth0ClientId`, `auth0Audience`, `apiOrigin`, and `portalOrigin` in `extension/config.js`; optional portal/API permissions are limited to those configured origins, while the separate ipify host permission is required and lookup remains off until explicitly enabled |

Do not place secrets, real telemetry logs, or approved user lists in the
repository. Public SPA Auth0 settings may appear in the frontend example file;
the API allowlist belongs only in ignored local or server-side environment
configuration and is never embedded in frontend bundles.

The intended production layout is the portal on Vercel, a static dashboard
(`dashboard/dist`) on Render, and a FastAPI Web Service on Render. The API
writes JSONL under `TELEMETRY_LOG_PATH`, which must be on a persistent disk
mounted at `/var/data`; set the path to `/var/data/telemetry_log.jsonl`.
Vercel serverless filesystems are not a durable telemetry store. Render's
`PORT` is supplied by the platform. The API start command is
`python -m uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`, with
`/api/health` as its health-check path. Both static sites use `npm ci &&
npm run build` and publish their component's `dist` directory. The API needs a
paid Web Service and persistent disk for this durable-storage design. **The
enterprise portal and API do not yet have a verified production deployment.**

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
origins. For staging, set the exact Vercel portal and API origins in
`extension/config.js`; the extension requests runtime host permission only for
those configured origins and dynamically registers its content script only on
the configured portal. The separate `api.ipify.org` host permission is used
only when public-IP lookup is explicitly enabled in the popup and telemetry
consent is active.

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
Copy-Item .env.example .env
.\scripts\run_local_api.ps1
```

The PowerShell launcher loads the ignored repository-root `.env` and starts
Uvicorn on `127.0.0.1:8765` with reload enabled. The API's Auth0 domain and
audience must match the portal's `VITE_AUTH0_DOMAIN` and
`VITE_AUTH0_AUDIENCE`. The configured audience is the custom ZeroKey API
identifier supplied for the selected Auth0 tenant; do not replace it with the
Auth0 Management API audience (`https://<tenant>/api/v2/`). Keep
`AUTH0_ALLOWED_SUBJECTS` empty until identities are explicitly approved;
protected data endpoints then return HTTP 503 while `/api/health` remains
available.

Vite reads `frontend/.env.local`, not `.env.example`. Copy the example once if
the local file is absent, then restart Vite after changing its values:

```powershell
if (-not (Test-Path frontend/.env.local)) {
    Copy-Item frontend/.env.example frontend/.env.local
}
npm --prefix frontend run dev
```

The local example uses the Auth0 client ID and domain supplied for this
workspace. The dashboard reads its own `dashboard/.env.local`; keep all
approved-subject values out of frontend files and Git.

The ZeroKey Portal SPA is configured with the `dev-g642lc64chdvl4p4`
Auth0 tenant and `https://zerokey-fyp-api` audience. The extension config uses
the same tenant, client ID, and audience. Its standalone popup login uses
`chrome.identity.getRedirectURL()`; that exact URL must be added to the
Auth0 application's Allowed Callback URLs if standalone extension sign-in is
used. The extension's exact `chrome-extension://` origin must also be added
to `CORS_ALLOWED_ORIGINS` after the unpacked extension ID is known.

The API exposes public `GET /api/health` and Auth0-protected
`GET /api/auth/check`, `POST /api/telemetry`, and
`GET /api/telemetry/recent`. Protected routes validate Auth0 RS256 access
tokens and require an exact allowlisted subject. Until
`AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, and `AUTH0_ALLOWED_SUBJECTS` are configured,
data access is denied. CORS is limited to the explicit configured origins (or
localhost development defaults) and does not replace token authentication.
The extension can look up the visitor's public IP using ipify's free
`https://api.ipify.org?format=json`
endpoint only after telemetry consent and when a behavioral activity window is
ready to send. The extension has a required, narrowly scoped `api.ipify.org`
host permission, but lookup remains off until explicitly enabled in the popup.
It caches a successful result in session-only extension storage for 15 minutes;
turning lookup off clears that cache. ipify receives the visitor's public IP,
which is a public egress address that can belong to a VPN, proxy, or shared
network and is not necessarily a unique user or their local network address.
If lookup is disabled or fails, feature data is still saved with a `null`
public IP.

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
2. In the extension popup, enable the configured portal once and grant the
   exact portal/API permissions. Reload the portal, sign in with an approved
   Auth0 identity, and choose **Allow telemetry** if you consent. The
   extension then receives the portal's short-lived API token, creates its
   SHA-256 device ID, and starts collecting without a second sign-in.
3. Use **Task 0 · Transcription** and **Task 1 · Survey** for typing practice.
   Select the authorized Session 0 PDF locally to read it while typing in
   Task 0. No exact-match check is performed. Task 1 displays the HTML
   questions and survey image. Task answers are practice-only: they are neither
   downloaded nor uploaded. With telemetry consent, only aggregated keyboard
   and mouse features are sent to the API. Then spend the planned 10 minutes navigating
   **Customers** and **Complaints & requests** and creating fictional tickets.
   Only opted-in aggregate features are sent as telemetry.
4. The extension popup reports whether the configured API is reachable. The
   dashboard's **Telemetry** page refreshes every five seconds; use its
   **Refresh** button to fetch immediately.
5. The dashboard retrieves recent records with its Auth0 access token.

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
allowlists match, the extension has permission for the configured portal, and
the API is running. Reload the extension from `chrome://extensions` and reload
the portal tab. Then open
**Complaints & requests** > **Create ticket**, type a few
fictional characters in **Complaint description**, then wait up to 15 seconds.
Check `http://127.0.0.1:8765/api/health` for backend status. Recent-record
requests require an approved Auth0 bearer token.
If the extension reports HTTP 422, reload the extension and portal after
updating them; the collector status now includes the API's rejected field and
validation message.

Each record contains the server-verified Auth0 subject as `user_id`, a SHA-256
device identifier, a per-tab session UUID (renewed after 30 minutes of
inactivity), an ISO timestamp, and only shortlisted mouse and keyboard
aggregates. The extension emits aggregate features rather than transmitting
typed text, raw event rows, coordinates, or key values. If public-IP lookup is
enabled, it also sends the public egress IP with the feature summary.

## Research data processing pipeline

The batch pipeline processes the research datasets under `data/raw/` without
changing the live browser telemetry collector. Session `0` is the default
training session. The session can be changed explicitly to `1` or `2`.

### Dataset inputs

Keystroke files are read from both condition directories:

```text
data/raw/UB_keystroke_dataset/s0/baseline/
data/raw/UB_keystroke_dataset/s0/rotation/
```

Each keystroke row contains a key name, `KeyDown` or `KeyUp`, and an integer
timestamp in milliseconds. Keystroke filenames use `UUUSKT.txt`: `UUU` is the
subject ID, `S` is the session, `K` is the keyboard code, and `T` is the task.
Keyboard codes are `0` Lenovo, `1` HP wireless, `2` Microsoft, and `3` Apple
Bluetooth. Task `0` is transcription; task `1` is free-text questions and
routine-work activities. The subset is derived only from the actual
`baseline` or `rotation` directory. The implementation validates that the
filename session agrees with the parent `s0`, `s1`, or `s2` directory.

Mouse files are cross-referenced by exact basename against valid keystroke
files across all sessions. A mouse file is selected for a requested session
only when it has exactly one keystroke counterpart whose documented session
matches. Mouse records preserve the original filename and suffix, and attach
the matched keystroke metadata under `keystroke_reference`. This is provenance
from the keystroke dataset, not independently documented mouse acquisition
semantics. Mouse condition, timestamp unit, epoch, synchronization, and event
alignment remain unknown; mouse records therefore use `condition: "unverified"`.
Unmatched and ambiguous mouse files are skipped and reported. The observed
suffix groups are `000/001`, `010/011`, `020/021`, `100/101`, `120/121`,
`130/131`, `200/201`, `210/211`, and `230/231`; these observations are not a
scientific whitelist for unseen data.

For example, the following meanings are verified for keystroke folders and
filenames, while the mouse fields are cross-referenced or unverified:

| Dataset | Example | Meaning |
| --- | --- | --- |
| Mouse | `001000.txt` | Original filename and suffix `000`; session/subset come from unique keystroke reference |
| Mouse | `001001.txt` | Original filename and suffix `001`; session/subset come from unique keystroke reference |
| Keystroke | `data/raw/UB_keystroke_dataset/s0/baseline/` | Session 0 baseline data |
| Keystroke | `data/raw/UB_keystroke_dataset/s0/rotation/` | Session 0 rotation data |

### Running the pipeline

Install development dependencies and run the default session:

```powershell
python -m pip install -r requirements-dev.txt
python -m src.data_pipeline.pipeline run --session 0
```

The default command also works without `--session`. To process another
supported session, pass `--session 1` or `--session 2`. Input and output roots
can be overridden with `--input-root` and `--output-root`.

### Outputs and cleaning

Session 0 writes:

```text
data/processed/keystroke_session0_processed.jsonl
data/processed/mouse_session0_processed.jsonl
data/processed/features_session0_processed.jsonl
```

Each line is one validated JSON object preserving the dataset, subject, session,
condition, raw filename suffix, original filename, event type, timestamp, source
file, and source line. Keystroke records also preserve the key, action,
`keyboard_code`, and `task_id`; mouse records preserve coordinates and the
exact-basename keystroke provenance. No timestamp conversion or cross-modality
alignment is performed.
Records are ordered by timestamp, source path, and source line. Exact repeated
reads of the same source line are deduplicated, while legitimate repeated
events on separate source lines remain. Invalid rows, unreadable files, and
unexpected formats are skipped with a warning and counted in the summary.
Non-finite numeric values cannot be written because JSON serialization uses
`allow_nan=False`; malformed records are never included in valid output.
Processed files are ignored by Git and generated locally by the pipeline.
Missing or removed UB subjects are skipped and never renumbered. Feature
records use the original three-digit subject ID as `user_id` and a deterministic
SHA-256 device ID derived from that subject and keyboard code. The UB feature
pipeline preserves nullable feature values as JSON `null` in each output row;
it does not drop rows for null feature values or impute them. There is currently
no separate model-training/imputation stage in this repository.

After collecting live records, verify their model/key schemas and compare the
UB feature summary with the live telemetry log before model training:

```powershell
python -m src.data_pipeline.sanity_check
```

The report validates each JSONL record against its own model, checks exact
record and feature keys, reports required/nullability differences, then checks
shared feature distributions. It exits nonzero on schema mismatches or
distribution differences. Some top-level metadata keys intentionally belong to
one record format only; those are listed separately from feature-key
differences. In particular, UB uses
`mouse_features.click_interval_ticks_mean`, with a null/unverified mouse
timebase in the current processed data, while live telemetry uses
`mouse_features.click_interval_ms_mean` in milliseconds (`performance.now()`).
The click intervals therefore cannot be treated as aligned or converted without
establishing the UB mouse timestamp rate. A distribution screen pass is not
proof of statistical equivalence.

To produce records with the UB feature-summary key structure, run the explicit
converter below. Its default assumes 1,000 UB mouse ticks per second (one
millisecond per tick); this is a conversion assumption, not a verified UB
dataset timebase:

```powershell
python -m src.data_pipeline.align_live
```

By default it reads the live telemetry log and processed UB feature files, then
writes `data/processed/telemetry_log_ub_aligned.jsonl`. It reserves subject IDs
already present in UB files and deterministically maps live user/session/device
identities into the UB field ranges. `subject_id`, `session`, `keyboard_code`,
`task_id`, `subset`, and `original_filename` are derived surrogates, not actual
UB experiment labels. The mapping is repeatable for the same input batch and UB
files; it is not evidence that the underlying users, sessions, tasks, or
conditions are equivalent. The converter refuses mappings that exceed UB's
identifier ranges and will not replace an existing output unless passed
`--overwrite`. Schema validity alone does not establish scientific suitability
for model training.

To summarize live feature nulls, write the live and UB device mapping files,
and verify feature names, dtypes, nullability, and column order (excluding
`device_id`), run:

```powershell
python -m src.data_pipeline.device_mapping
```

The command reads the live telemetry log and processed UB feature JSONL. It
validates and aligns live records first, including the configured click-interval
conversion, then writes `data/processed/live_device_mapping.jsonl` and
`data/processed/ub_device_mapping.jsonl`. Live mappings retain captured
`user_id`/`device_id` pairs. UB mappings use a stable SHA-256-derived synthetic
device ID per `user_id`. The null report distinguishes nulls from absent source
keys; legitimate nulls remain null rather than being imputed, and live rows are
not dropped for nullable feature values, matching the UB preprocessor. The
report also shows how many UB and live rows contain any null feature. Invalid
required fields fail validation. These local data files are not replaced unless
`--overwrite` is passed.

Illustrative input and output records:

```text
Input:  LMenu KeyDown 63578429757751
Output: {"action":"KeyDown","condition":"baseline","dataset":"keystroke","event_type":"keyboard","filename_suffix":"000","keyboard_code":0,"key":"LMenu","line_number":1,"original_filename":"001000.txt","session":0,"source_file":"data/raw/UB_keystroke_dataset/s0/baseline/001000.txt","subject_id":"001","task_id":0,"timestamp":63578429757751}

Input:  635784297580483748 | ... | Mouse Coordinates | 611,676
Output: {"condition":"unverified","dataset":"mouse","event_type":"mouse_move","filename_suffix":"000","keystroke_reference":{"keyboard_code":0,"mapping_basis":"unique_exact_basename_match","session":0,"source_file":"data/raw/UB_keystroke_dataset/s0/baseline/001000.txt","subject_id":"001","subset":"baseline","task_id":0},"line_number":12,"original_filename":"001000.txt","session":0,"source_file":"data/raw/UB_mouse_and_events_dataset/001000.txt","subject_id":"001","timestamp":635784297580483748,"x":611,"y":676}
```

### Tests

Run the full suite with:

```powershell
python -m pytest
```

### Research-use restriction and citation

The UB Keystroke Dataset is for research purposes only and must not be used
commercially. Academic or research reports using it must cite: Yan Sun,
Hayreddin Ceker, and Shambhu Upadhyaya, “Shared Keystroke Dataset for
Continuous Authentication,” 8th IEEE International Workshop on Information
Forensics and Security, Abu Dhabi, UAE, December 2016.
