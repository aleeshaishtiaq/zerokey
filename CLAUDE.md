# ZeroKey — instructions for every chat

ZeroKey is a Final Year Project (NUCES Islamabad): a Chrome extension for
continuous post-login authentication. It collects privacy-preserving keyboard
and mouse feature summaries on an enterprise demo portal, stores them through a
FastAPI API in Supabase Postgres, shows them on a security dashboard, and will
train per-user One-Class SVM models.

Team members work in separate chats, each with their own copy of this repo.
Chats do not share memory, so this file and `docs/PROGRESS.md` are the shared
memory. Keep both current.

## Start of every chat
1. Run `git pull` on `develop` (or ask the member to) before changing anything.
2. Read `docs/PROGRESS.md` to see what the other members did last.
3. Ask who is speaking if it is not clear. Members should start with their name
   (for example "Areeba:"). Never assume which member is typing.

## End of every task
1. Add a short dated entry to the top of the log in `docs/PROGRESS.md`:
   who, what changed, what is still open.
2. Commit on a feature branch, push, open a PR into `develop`.
3. Tell the member to use **Squash and merge** on GitHub.

## Rules the team asked for
- Do not mention Claude, Anthropic or AI in commit messages, PR titles or PR
  descriptions. No `Co-Authored-By` or session lines. Commit author is the
  member doing the work.
- Replies to the team are in Roman Urdu, calm, polite and step by step.
- Change only what the member asked for. Do not touch other parts of the
  project.
- Never commit data: `data/` is gitignored. Supabase CSV exports contain user
  IDs and IP addresses.

## Git workflow
- Branches: `feature/...`, `fix/...`, `docs/...` off `develop`; PR into `develop`.
- CI (`.github/workflows/ci.yml`) runs on PRs and on pushes to `develop`/`main`:
  `python -m flake8 src/ tests/ --max-line-length=100 --extend-ignore=E501`,
  `python -m pytest tests/ -q`, and both frontend builds.
- CD (`.github/workflows/cd.yml`) deploys the API to Vercel after CI passes on a
  push to `develop`. Merging into `develop` = production API deploy.
- Members are on Windows; git converts line endings (CRLF warnings are normal).
- Local checks before pushing (from the repo root, in PowerShell):
  `.\.venv\Scripts\python.exe -m pytest tests -q` and the flake8 command above.

## Where things are
| Part | Path | Live URL |
|---|---|---|
| Extension (MV3) | `extension/` — config in `extension/config.js` | loaded unpacked in Chrome |
| Portal (Vite) | `frontend/` | https://zerokey-2fvk.vercel.app |
| API (FastAPI) | `src/api/` (`routes.py`, `auth.py`, `settings.py`) | https://zerokey-five.vercel.app/api |
| Database code | `src/data/database.py` (table `telemetry_records`) | Supabase |
| Dashboard (React) | `dashboard/` — run with `scripts\start_dashboard.bat` | http://localhost:5173 |
| UB data pipeline | `src/data_pipeline/` | — |
| Training windows | `src/data_pipeline/prepare_training_windows.py` | — |

Portal, dashboard and extension all call the deployed API, not a local one.

## Facts that are easy to get wrong
- The session IP is the value the **extension** sends (ipify, then Amazon
  checkip). The server does not derive it. After changing the extension, bump
  `version` in `extension/manifest.json` and reload it in `chrome://extensions`;
  an old loaded version is the usual reason data looks wrong.
- Database timestamps are UTC (`+00`). Pakistan time = UTC + 5.
- Live telemetry is one row per 15-second window (`WINDOW_DURATION_MS` in
  `extension/content.js`), keyboard and mouse combined.
- UB keystroke timestamps are milliseconds; UB mouse timestamps are .NET ticks
  (10,000,000 per second).
- `inter_key_interval_ms_stddev` always equals `pp_latency_ms_stddev`; it is
  excluded from training. `click_interval_ms_mean` is excluded too (almost
  always undefined in a 15 s window).
- Browsers report a touchpad as `pointerType = "mouse"`; there is no reliable way
  to tell them apart. ZeroKey does **not** label the device: extension 1.5.3+
  sends device signals in `mouse_features` (`pointer_event_rate_hz`,
  `coalesced_events_per_move`, `wheel_event_count`, `wheel_smooth_ratio`) and
  training builds several input profiles per user. See
  `docs/input-profiles-design.md`.
- The API forbids unknown fields. When the extension sends a new field, deploy
  the API first, then reload the extension.

## Training data
`python -m src.data_pipeline.prepare_training_windows --live-file data\raw\zerokey_captured\telemetry_records_rows.csv`
(add `--live-test-from YYYY-MM-DD` once a later live round exists) builds, in
`data/processed/training/`, for each source (`ub`, `live`), modality
(`keyboard`, `mouse`) and split (`train`, `calibration`, `test`):
`<source>_<modality>_<split>_clean.jsonl` and `..._normalized.jsonl`, plus
`live_mouse_device_signals.jsonl` (1.5.3+ windows only),
`normalization_params.json` and `data_quality_report.json` (windows per user
per split). No nulls, no IP, no window in two splits.
- Keyboard windows: 10 absolute + 5 relative timing features. Mouse: 5.
- UB subjects with < 60 mouse windows (021, 049, 127) are left out of the mouse
  files; their keyboard windows stay.
- Splits are chronological. UB: train = session 0 + first 60% of session 1,
  calibration = rest of session 1, test = session 2. Live is split **inside
  every session** in time order, so every session (for example a
  touchpad-only one) also reaches train. Planned: round 1 (data up to 26 Nov)
  = 75% train / 25% calibration per session, and a second collection round
  after a gap = test (`--live-test-from <first day of round 2>`). Until round 2
  exists, each session is split 60% / 20% / 20%, so the training code can be
  built and checked; final live results use round 2.
- Normalized files use a median/IQR scaler fitted on the **train** split only.
- Live users are relabelled `L01`, `L02`, ... by sorted user ID; the real ID
  stays in `user_id`.
- Round 1 live export: `data/raw/zerokey_captured/telemetry_round1_train_calibration_2026-11-26.csv`.
  For round 2, save the new full export in the same folder and pass it with
  `--live-file` plus `--live-test-from`.
- The UB folders are large; if the run is slow on a mounted drive, copy them
  to a local disk first.
- `data/` is gitignored. Training data is shared as a zip outside git.

## Model training (Azka)
Plan: 3 one-class models per user and modality, compared, best one selected.
1. **Models:** One-Class SVM, Isolation Forest, Autoencoder (LOF if the
   autoencoder runs out of time).
2. **Micro model = per user, per modality.** Each user gets a keyboard model
   and a mouse model, trained only on that user's `train` windows. A user
   without mouse data (UB 021, 049, 127) gets a keyboard model only; that is
   expected (like a new employee whose mouse is not enrolled yet), not an
   error. Leave them out of the mouse averages only.
3. **Splits:** fit models on `train`; choose thresholds and risk-state
   boundaries on `calibration`; report final EER / FAR / FRR / AUC on `test`
   only. Never tune on `test`.
4. **Scaling:** either fit a scaler per user on that user's `train` clean
   windows, or use the `_normalized` files (already fitted on train). Never fit
   anything on calibration or test.
5. **Impostors:** other users' windows from the **same source and split**
   (UB vs UB, live vs live). Never use UB windows as impostors for live users.
6. **Features:** run every model twice for keyboard: 10 absolute features
   only, and all 15 (absolute + relative). Report both; keep the better set.
7. **Fusion:** live keyboard and mouse rows of the same window share
   `session_id` + `window_index`; fuse scores only where both exist in the same
   split. UB keyboard and mouse are separate recordings: report them per
   modality.
8. **Main results come from UB** (148 users). Live (2 users) shows that the
   same pipeline works on ZeroKey's own data.
9. **Live test data:** final live results must come from a **second
   collection round** (Areeba and Aleesha, after a 2-3 day gap; one week is
   better). When Azka's training code is ready, she tells the team that live
   round 2 is needed; after it is collected, export again and rerun the
   pipeline with `--live-test-from <first day of round 2>`. Until then the
   live test split is only an interim check (last 20% of 23-26 Nov). Note in
   the report that the live gap is shorter than UB's (about 4 weeks), so live
   results may look a little better than UB results.
10. Document training configs, logs, metrics, and limitations as Iteration 2
    evidence.

## Risk decision contract (until the Shadow Environment exists)
The Shadow Environment is built later. Until then, any component that maps a
score to a risk state must still **decide and record** the action:
- Output for every scored window: `risk_state` (CONTINUE / MONITOR / STEP_UP /
  LOSS_OF_PRIVILEGES / TERMINATE / SHADOW), the score(s) used, the threshold
  that was crossed, and a short `reason`.
- When the state is `SHADOW`, log `decision = "SHADOW"` with its reason and
  return `action_status = "not_implemented"` (no redirect yet). The redirect
  is wired in when the Shadow Environment is built; the decision logic does
  not change then.
