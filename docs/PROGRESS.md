# ZeroKey progress log

Newest entry first. Every chat adds an entry here at the end of its task
(see `CLAUDE.md`). Keep entries short: who, what, what is still open.

## Open items
- [ ] **Touchpad support** (Areeba, next chat): extension sends
  `pointer_type` (`mouse` / `touchpad`) with each window, portal gets a small
  Mouse/Touchpad choice, API + `telemetry_records` get a `pointer_type`
  column, `prepare_training_windows.py` writes mouse and touchpad to separate
  files and can label older rows by user + time range. Bump the extension to
  1.5.3. Deploy the API before collecting touchpad data.
- [ ] Confirm that Areeba's 30-minute keyboard session on Aleesha's laptop was
  saved under **Areeba's** account, not Aleesha's (check `user_id` of those
  rows in a fresh export). If it was Aleesha's account, those rows must be
  removed from training.
- [ ] Finish data collection (targets below), then export again and rerun
  `prepare_training_windows.py`.
- [ ] Train per-user One-Class SVM models (keyboard on normalized windows;
  mouse/touchpad per input type).

## Data collection status
Targets per member: 250 keyboard windows, 150 mouse windows, 4+ sessions on 2+
days (1 window = 15 s of activity). From the Supabase export of 2026-11-26.
Live IDs: `L01` = google-oauth2|1093… (data 23–24 Nov, believed to be
Areeba), `L02` = google-oauth2|1099… (data 24–25 Nov, believed to be Aleesha).
Confirm and correct if needed.

| Member | Keyboard | Mouse | Sessions | Still needed |
|---|---|---|---|---|
| Areeba (L01) | 125 + ~30 min on Aleesha's laptop (not yet counted) | 54 | 2 | ~12–15 min mouse; touchpad ~25 min once supported |
| Aleesha (L02) | 128 | 116 | 8 | ~30 min typing |

Rules while collecting: extension 1.5.2 on, consent given, sign out and sign in
with your own account on someone else's laptop, type in your own words (no
copy-paste), do not leave the portal idle, note the time of any touchpad
session.

## Log

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
- Added this file and `CLAUDE.md`.
