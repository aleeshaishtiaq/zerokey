# ZeroKey progress log

Newest entry first. Every chat adds an entry here at the end of its task
(see `AGENTS.md`). Keep entries short: who, what, what is still open.

## Open items
- [ ] **Deploy order for extension 1.5.3:** merge the device-signals PR into
  `develop` (API deploys), check `/api/health`, and only then reload the
  extension in `chrome://extensions`. The old API rejects 1.5.3 windows (422)
  because unknown fields are forbidden.
- [ ] Model training (Azka): 3 one-class models (One-Class SVM, Isolation
  Forest, Autoencoder) per user and modality on the `train` split, thresholds
  on `calibration`, final metrics on `test`; compare and pick the best. Rules
  in `AGENTS.md` > "Model training (Azka)". Input-profile clustering comes
  later (see `docs/input-profiles-design.md`).
- [ ] Live round 2 (Areeba, Aleesha) for the final live **test** split: collect
  after a 2-3 day gap (one week better), when Azka says her training code is
  ready; then export and rerun with `--live-test-from <first day of round 2>`
  (23-26 Nov data then becomes 75% train / 25% calibration per session).
- [ ] Later: profile clustering + gatekeeper / step-up flow from
  `docs/input-profiles-design.md` (max 7 profiles, removal only after 1 year
  unused, 8th profile -> admin review).

## Data collection status
Targets per member: 250 keyboard windows, 150 mouse windows, 4+ sessions on 2+
days (1 window = 15 s of activity). **All targets met** (Supabase export of
2026-11-26, 832 rows, 23-26 Nov).

| Live ID | Member | Keyboard | Mouse | Sessions | Days (PKT) | Devices |
|---|---|---|---|---|---|---|
| `L01` = google-oauth2\|1093... | Areeba | 289 | 158 | 4 | 23, 24, 26 Nov | own laptop + Aleesha's laptop |
| `L02` = google-oauth2\|1099... | Aleesha | 253 | 245 | 9-11 | 24, 25, 26 Nov | own laptop |

Areeba's typing session on Aleesha's laptop (26 Nov, ~11:45-12:55 PKT, 160
rows on Aleesha's device ID) was saved under Areeba's account, so it is valid
training data.

## Log

### 2026-11-26 (evening) — Areeba
- Extension 1.5.3 tested after the API deploy: rows arrive with the four
  device signals (the portal tab must be refreshed after reloading the
  extension).
- Added 30 minutes of **touchpad-only** data (L01, 20:40-21:10 PKT, 122 mouse
  windows, all with `wheel_smooth_ratio = 1.0` when scrolling).
- Live split is now done **inside every session** (60/20/20 interim; 75/25
  train/calibration once round 2 exists), so the touchpad session also
  reaches train (74 / 24 / 24 windows). New test in
  `tests/test_training_windows_rules.py`; full suite 59 passed.
- Round 1 live export renamed to
  `telemetry_round1_train_calibration_2026-11-26.csv` (954 rows). Training
  data rebuilt (UB unchanged; live keyboard 337 / 110 / 104, live mouse
  322 / 104 / 99) and sent to Azka as zip v4.
- Pointer devices in the live data (stated by the members):
  - **L02 (Aleesha): all pointer data is touchpad.** She does not use a mouse
    and cannot give mouse data; her pointer model is a touchpad model.
  - L01 (Areeba): the 122 windows of 26 Nov 20:40-21:10 are touchpad (with
    device signals). For her earlier windows (23-26 Nov, before 1.5.3) the
    device is not known.

### 2026-11-26 — Areeba
- Touchpad support, redesigned: no `mouse`/`touchpad` label (browsers cannot
  tell them apart; a calibration test showed no reliable fixed threshold).
  Instead the extension (now **1.5.3**) sends four device signals in
  `mouse_features`: `pointer_event_rate_hz`, `coalesced_events_per_move`,
  `wheel_event_count`, `wheel_smooth_ratio`. Design: `docs/input-profiles-design.md`.
- API: the four fields are optional (old extensions still work). Database: four
  nullable columns, added to the existing table automatically on first use.
- `align_live.py`: drops the device signals before UB-schema validation.
- `prepare_training_windows.py`: writes `live_mouse_device_signals.jsonl`
  (only 1.5.3+ windows; empty for now). Clean UB/live files are unchanged.
- `prepare_training_windows.py` also:
  - adds 5 **relative timing features** to every keyboard window (UB and live):
    `dwell_time_cv`, `pp_latency_cv`, `rp_latency_cv`, `dwell_to_pp_ratio`,
    `rp_to_pp_ratio`. On UB, the keyboard-change ("rotation") group shifted
    2-3x less on these than on absolute timings between sessions. Absolute
    features are kept; training should compare 10 vs 15 keyboard features.
  - leaves UB subjects with < 60 mouse windows out of the mouse files
    (`MIN_UB_MOUSE_WINDOWS_PER_SUBJECT`; drops 021, 049, 127; their keyboard
    windows stay).
- Tests: `tests/test_device_signals.py`, `tests/test_training_device_signals.py`,
  `tests/test_training_windows_rules.py`; `test_sanity_check.py` updated for the
  live-only device signals.
- Training files are now split chronologically into `train` / `calibration` /
  `test` (UB: session 0 + 60% of session 1 / rest of session 1 / session 2;
  live: interim 60/20/20 per user and modality until live round 2 exists, then
  round 1 = 75/25 train/calibration and round 2 = test). The normalization
  scaler is fitted on
  train only. Azka's instructions and the risk-decision contract (SHADOW is
  decided and logged, redirect not implemented yet) are in `AGENTS.md`.
- Rebuilt `data/processed/training/` from the 26 Nov export: UB 62,592 keyboard
  windows (148 users, sessions 0-2) / 16,587 mouse windows (145 users), live
  542 keyboard / 403 mouse windows; no nulls, no IP, no duplicates. Sent to
  Azka as `zerokey_training_data_2026-11-26.zip` (data/ is gitignored).
  Per split: UB keyboard 33,809 / 8,277 / 20,506, UB mouse 8,722 / 2,260 /
  5,605, live keyboard 326 / 109 / 107, live mouse 242 / 81 / 80.
- Full test suite: 57 passed.
- Not done: profile clustering and gatekeeper/step-up (design only).

### 2026-11-26 — Aleesha
- Merged PR #17 into `develop` (deployed; `/api/health` returns
  `{"status":"ok","storage":"database"}`):
  - Database: `DATABASE_URL` normalisation, table/columns created
    automatically, NullPool on Vercel, recent telemetry newest-first.
  - API: `.env` loaded locally, DB errors logged, clear 503 if `DATABASE_URL`
    is missing on Vercel, `/api/telemetry/status`.
  - Dashboard: "Session IP" column, API error details shown.
  - `prepare_training_windows.py`: UB + live 15-second windows, separate
    keyboard/mouse files, no IP, no nulls, normalized copies.
  - Helpers: `scripts/run_tests.bat`, `scripts/start_dashboard.bat`.
- Found: the IP was empty because Chrome still ran extension 1.5.0; reloading
  1.5.2 fixed it.
- Not committed on purpose: Cursor debug logging in `extension/background.js`
  (left in the local stash).
- Added this file and `AGENTS.md`.
