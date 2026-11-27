# ZeroKey progress log

Newest entry first. Every chat adds an entry here at the end of its task
(see `AGENTS.md`). Keep entries short: who, what, what is still open.

## Open items
- [ ] **Extension 1.6.0 (feature set v2 + mouse v3) deploy order:** merge the
  `feature/extension-v2-features` PR into `develop`, wait for CD, check
  `/api/health`, then reload the extension in `chrome://extensions` and
  refresh the portal tab. The old API rejects 1.6.0 windows (422).
- [ ] **New live round 1 with extension 1.6.0 (Areeba, Aleesha):** two days,
  2-3 sessions per day, per member per day about 1 hour of typing and about
  1-1.5 hours of mouse/touchpad only (normal portal work: clicking, scrolling,
  forms). Then export and rebuild with `--live-from <first day of the round>`
  (the 23-26 Nov rows have no v2/v3 and are left out of these files). Round 2
  (test) follows after a gap, with `--live-test-from`.
- [ ] **Deploy order for extension 1.5.3:** merge the device-signals PR into
  `develop` (API deploys), check `/api/health`, and only then reload the
  extension in `chrome://extensions`. The old API rejects 1.5.3 windows (422)
  because unknown fields are forbidden.
- [ ] Model training (Azka): 3 one-class models (One-Class SVM, Isolation
  Forest, Autoencoder) per user and modality on the `train` split, thresholds
  on `calibration`, final metrics on `test`; compare and pick the best. Rules
  in `AGENTS.md` > "Model training (Azka)". Input-profile clustering comes
  later (see `docs/input-profiles-design.md`). Steps 1-2 (UB keyboard, UB
  mouse) done on 27 Nov; live and fusion still open.
- [ ] **Feature set v2 (Areeba):** UB part **done 27 Nov** (zip v5 sent to
  Azka). Next: Azka compares v1 vs v2 on UB; **only if v2 helps**, add the
  same features to the API and the extension and collect a new live round 1
  (one day, 2-3 sessions; only the modality that improved), then rebuild
  with `--live-from <first day of the new round>`.
  **Azka compared v1 vs v2 on 27 Nov (see Log): keyboard v2 helps clearly,
  mouse v2 helps a little.** Team decides which modality goes into the
  extension.
  Keep every current feature, so old and new results can be compared.
  Mouse v3 (per-stroke features) added for UB on 28 Nov (zip v6); the
  extension update waits for Azka's v3 tests.
  - Mouse: speed std / median / p90, acceleration (mean, std, p90), jerk
    (mean, median, p90), right-click count. In the 27 Nov test these were the
    most useful (jerk and acceleration first).
  - Keyboard: backspace rate (a count only, no key text), median dwell /
    press-press / release-press, and release-release latency.
  - The same features must come from the extension for live data
    (`extension/content.js`) and be accepted by the API: deploy the API first,
    then bump the extension version and reload it.
  - Note: the old `src/data_pipeline/parsers.py` click pattern does not match
    UB click lines (`| Left | Click`); `prepare_training_windows.py` reads them
    correctly, so the current training data is not affected.
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

### 2026-11-28 (night) — Areeba
- Decision (team): option (a), extension and API get keyboard v2, mouse v2 and
  mouse v3 together, so the extension and the live round change only once.
  A quick check on the 23-26 Nov live data (old v1 features, 2 users, ~50
  test windows each, so noisy): keyboard EER ~0.27 per window, ~0.21 with
  1-minute decisions (One-Class SVM); mouse ~0.46, ~0.42 with 1 minute, about
  the same as UB.
- Extension **1.6.0**: new `extension/features.js` (loaded before
  `content.js`) holds the v2 mouse kinematics and the mouse v3 stroke features
  with the same formulas as `prepare_training_windows.py`; `content.js` adds
  keyboard v2 (backspace count via `event.code` only, medians,
  release-release) and right clicks (`mousedown`, button 2).
- API and database: 28 optional fields / nullable columns (6 keyboard, 22
  mouse), added to the existing table automatically on first use.
  `align_live.py` drops them before the old UB-schema validation.
- Tests: `tests/test_extension_parity.py` runs the real `content.js` in node
  (`tests/extension_harness.js`) and checks that every v1/v2/v3 value equals
  the Python pipeline for the same events (skipped where node is missing);
  `tests/test_api_feature_set_v2.py`; `test_sanity_check.py` and
  `test_telemetry.py` updated for the new live-only fields. Full suite 94
  passed.

### 2026-11-28 — Azka
- Zip v6 unpacked (checksums OK). Training code: mouse set `mouse27`
  (5 v1 + 10 v2 + 12 v3) in `src/training/data.py`, and two options in
  `train_ub`: `--min-strokes N` (mouse; keeps windows with
  `stroke_count >= N` in every split; coverage = share of test windows kept)
  and `--decision-windows K` (one decision = mean score of K consecutive
  windows of the same session; 4 = 1 minute; same rule on calibration and
  test). Thresholds still come from calibration only.
- The four agreed UB mouse tests (test EER / AUC, mean over users):

  | Test | Coverage | One-Class SVM | Isolation Forest | Autoencoder |
  |---|---|---|---|---|
  | mouse15 (v2, reference) | 100% | 0.458 / 0.563 | 0.461 / 0.560 | 0.455 / 0.561 |
  | 1. option 3: mouse27 | 100% | 0.452 / 0.573 | 0.456 / 0.564 | 0.451 / 0.573 |
  | 2. 3 + 1: strokes >= 2 | 80% | 0.443 / 0.586 | 0.449 / 0.577 | 0.441 / 0.583 |
  | 2. 3 + 1: strokes >= 4 | 48% | 0.434 / 0.595 | 0.447 / 0.583 | 0.435 / 0.589 |
  | 3. 3 + 2: 4 windows (1 min) | 100% | 0.431 / 0.598 | 0.446 / 0.579 | 0.434 / 0.584 |
  | 4. 3 + 1 + 2: strokes >= 2, 1 min | 80% | **0.417 / 0.617** | 0.432 / 0.598 | 0.426 / 0.601 |
  | 4. 3 + 1 + 2: strokes >= 4, 1 min | 48% | 0.406 / 0.627 * | 0.439 / 0.590 * | 0.424 / 0.596 * |

  \* only 126 of 145 users get a decision (too few windows left).
  Reference for option 2 alone: mouse15 with 1-minute decisions gives
  0.446 / 0.453 / 0.444.
- Option 3 alone is not a clear gain: per user, mouse27 beats mouse15 for
  71-75 users and loses for 59-64 (sign test p 0.19-0.61). Options 1 and 2
  help more; the best mouse result is 3 + 1 + 2 (One-Class SVM, strokes >= 2,
  1 minute): EER 0.417 at 80% coverage. UB mouse stays weak (AUC about 0.6).
- Keyboard (abs10_v2) with option 2, for comparison: 1 window 0.268-0.269,
  4 windows (1 min) 0.226 (Isolation Forest) / 0.228 (One-Class SVM),
  8 windows (2 min) 0.207 (One-Class SVM) / 0.209 (Isolation Forest).
  Decisions over several windows are the biggest gain so far.
- Suggestion for the one extension + API update: keyboard v2 (clear gain);
  for mouse, v3 adds little on UB, so it is a team call (UB users mostly type;
  live portal data may move the mouse more). Multi-window decisions and
  minimum strokes need no new data.
- Still open: live models and fusion, saving the fitted models, choosing K
  and the minimum strokes on calibration, model tuning on calibration.

### 2026-11-28 — Areeba
- Team decision after Azka's v1 vs v2 result: keyboard v2 helps; for mouse,
  try **option 3** (per-stroke features) before changing the extension, so the
  extension and the live round change only once. Test order on UB: option 3
  alone, 3 + 1 (minimum strokes per window), 3 + 2 (several windows per
  decision), then 3 + 1 + 2.
- Mouse v3 in `prepare_training_windows.py` (UB): a stroke is movement with no
  pause over 300 ms (at least 4 samples, 10 px); a click stroke is followed by
  a left click within 1 s. 12 window features (`V3_MOUSE_FEATURES`): stroke
  count, median duration / length / efficiency (+ mean) / deviation /
  curvature / peak speed / time-to-peak, share of sideways strokes, share of
  click strokes, median pause before the click. No window dropped; windows
  without a stroke (3.3%) have `stroke_count` = 0. Every v1/v2 value is
  identical to v5.
- Quick check (Isolation Forest, test EER, UB mouse): mouse15 0.460 ->
  mouse27 0.454; 1-minute decisions 0.437; plus `stroke_count` >= 2: 0.428 at
  81% coverage. For keyboard, 1-minute decisions: 0.266 -> 0.232 (2 min
  0.214). Mouse improves only a little on UB (UB users mostly type); live
  portal data may move the mouse more.
- Tests: `tests/test_mouse_v3.py`; full suite 83 passed.
- Zip **v6** for Azka (`zerokey_training_data_v6.zip`): UB mouse 27 features;
  keyboard and live unchanged.
- Next: Azka runs the four tests; then one extension + API update (keyboard
  v2 and the mouse sets that help), then one live round.

### 2026-11-27 (late night) — Azka
- Zip v5 unpacked (checksums OK; live files unchanged). Feature set v2 added
  to `src/training/data.py`: keyboard `abs10_v2` (10 absolute + 6 v2) and
  `all21` (all), mouse `mouse15` (5 + 10 v2). `train_ub` now runs every set by
  default. v1 results are identical to before, so v1 vs v2 is a fair test.
- UB, test split, one 15 s window per decision, mean over users:

  | Modality | Model | v1 EER / AUC | v2 EER / AUC |
  |---|---|---|---|
  | Keyboard (abs10 -> abs10_v2) | One-Class SVM | 0.288 / 0.755 | 0.269 / 0.774 |
  | Keyboard (abs10 -> abs10_v2) | Isolation Forest | 0.296 / 0.749 | **0.268 / 0.780** |
  | Keyboard (abs10 -> abs10_v2) | Autoencoder | 0.294 / 0.753 | 0.293 / 0.752 |
  | Mouse (mouse5 -> mouse15) | One-Class SVM | 0.474 / 0.539 | 0.458 / 0.563 |
  | Mouse (mouse5 -> mouse15) | Isolation Forest | 0.471 / 0.541 | 0.461 / 0.560 |
  | Mouse (mouse5 -> mouse15) | Autoencoder | 0.472 / 0.540 | 0.455 / 0.561 |

  `all21` (with the 5 relative features) is slightly worse than `abs10_v2`
  (best 0.271), so the relative features still do not help.
- Per user (EER v1 vs v2): keyboard Isolation Forest better for 124 users,
  worse for 23; One-Class SVM 107 / 39 (both clearly beyond chance, sign test
  p < 1e-7); autoencoder 85 / 61 (no clear change). Mouse: 84-93 users better,
  47-55 worse (small but consistent gain; mouse still close to chance).
- Conclusion: keyboard v2 is worth adding to the extension and API; mouse v2
  gives only a small gain (team decision). New best keyboard model: Isolation
  Forest with `abs10_v2`.
- Still open: combining consecutive windows, live models and fusion, saving
  the fitted models, model tuning on calibration.

### 2026-11-27 (night) — Areeba
- Feature set v2 in `prepare_training_windows.py` (UB), added next to every
  existing feature:
  - Keyboard (6): `backspace_rate` (count only; UB key `Back`, browser
    `Backspace`), `dwell_time_ms_median`, `pp_latency_ms_median`,
    `rp_latency_ms_median`, `rr_latency_ms_mean`, `rr_latency_ms_median`
    (release-release, consecutive releases under 500 ms).
  - Mouse (10): speed std / median / p90, acceleration mean / std / p90, jerk
    mean / median / p90 (from consecutive movement samples inside a burst;
    acceleration and jerk are absolute changes per second), and
    `right_click_count` (UB `| Right | Click`).
  - A v2 value that cannot be computed in a window is 0.0 (counted in the
    report): ~1.8% of UB mouse windows (jerk), 0.06% of UB keyboard windows.
    No window is dropped; every v1 value is identical to v4 (checked).
  - Live: rows without v2 keep the v1 schema; if old and new live rows are
    mixed, v2 is left out of that file. New option `--live-from <date>` keeps
    only live windows from that date on (for a new live round with the v2
    extension).
- UB mouse is sampled every ~15.6 ms; UB keyboard timestamps also move in
  ~15.6 ms steps, so many timing values repeat (property of the raw data).
- Tests: `tests/test_feature_set_v2.py`; full suite 77 passed (including the
  training tests with scikit-learn).
- Training data zip **v5** for Azka (`zerokey_training_data_v5.zip`): same
  windows and splits as v4; UB keyboard 21 features, UB mouse 15; live
  unchanged. Azka adds the v2 feature-set names to `src/training/data.py`.
- Not done yet (waits for Azka's v1 vs v2 result): v2 in the API and the
  extension, new live round.

### 2026-11-27 — Azka
- Model training, step 1 (UB keyboard only), on branch `feature/model-training`:
  - `src/training/`: data loading (`data.py`), One-Class SVM / Isolation Forest /
    MLP autoencoder per user (`models.py`, scikit-learn), FAR / FRR / EER / AUC
    (`metrics.py`), and `python -m src.training.train_ub_keyboard`.
  - Each user's model and scaler are fitted on that user's `train` windows; the
    threshold is set where FAR = FRR on `calibration`; metrics are on `test`.
    Impostors = the other UB users of the same split.
  - Training packages are in `requirements-training.txt` (not in
    `requirements.txt`, so the Vercel API stays small).
  - Output (gitignored): `data/processed/models/ub_keyboard/<run>/`
    (`per_user_metrics.csv`, `summary.json`, `config.json`, `run.log`).
  - Tests: `tests/test_training_models.py` (skipped where scikit-learn is not
    installed, for example in CI).
- First full run (148 users, one 15 s window per decision, mean over users):

  | Model | Features | Test EER | Test AUC | Test FAR | Test FRR |
  |---|---|---|---|---|---|
  | One-Class SVM | 10 | 0.288 | 0.755 | 0.381 | 0.220 |
  | One-Class SVM | 15 | 0.290 | 0.753 | 0.390 | 0.221 |
  | Isolation Forest | 10 | 0.296 | 0.749 | 0.427 | 0.218 |
  | Isolation Forest | 15 | 0.293 | 0.752 | 0.426 | 0.215 |
  | Autoencoder | 10 | 0.294 | 0.753 | 0.417 | 0.210 |
  | Autoencoder | 15 | 0.301 | 0.742 | 0.419 | 0.227 |

  The models are close; One-Class SVM with 10 features is best so far. The 5
  relative features do not help yet. FAR on test is higher than the
  calibration EER because test (session 2) is weeks later.
- Step 2 (UB mouse): training now runs per modality with
  `python -m src.training.train_ub --modality keyboard|mouse`
  (`train_ub_keyboard` still works). 145 users, 5 mouse features:

  | Model | Test EER | Test AUC | Test FAR | Test FRR |
  |---|---|---|---|---|
  | One-Class SVM | 0.474 | 0.539 | 0.468 | 0.475 |
  | Isolation Forest | 0.471 | 0.541 | 0.463 | 0.477 |
  | Autoencoder | 0.472 | 0.540 | 0.463 | 0.482 |

  Mouse is close to chance. This is the features, not the split: a random
  70/30 split inside each user's own train windows also gives AUC about 0.54,
  and for every mouse feature the spread between users is only 0.25-0.38 of
  the spread inside one user. Better mouse results need richer mouse features
  (team decision; the data pipeline was not changed).
- Raw UB check and mouse feature test (outside the repo, same 15 s windows
  and splits as the pipeline; the 5 current features gave the same results):
  - Raw UB mouse has only position, time, Left/Right clicks (no press/release)
    and the active window. The raw files also hold the lab computer name,
    user name and IP: keep them in `data/raw/` only.
  - 33 mouse features (speed, acceleration, jerk, curvature, strokes, pauses,
    clicks): test AUC 0.54 -> 0.58 (One-Class SVM EER 0.474 -> 0.447,
    autoencoder 0.471 -> 0.443). Better, but UB mouse stays weak: the median
    mouse window is active only about 21% of the time (about 600 px of
    movement), because UB users mostly type. Keyboard stays the main signal.
  - Agreed with the team: Areeba redoes the preprocessing with feature set v2
    (see Open items).
- Still open: live keyboard/mouse, score fusion, combining consecutive
  windows, model tuning on calibration, saving the fitted models, retraining
  on feature set v2.

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
