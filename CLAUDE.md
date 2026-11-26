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
- Browsers report a touchpad as `pointerType = "mouse"`; it cannot be told apart
  from a mouse without extra logic.

## Training data
`python -m src.data_pipeline.prepare_training_windows --live-file data\raw\zerokey_captured\telemetry_records_rows.csv`
builds, in `data/processed/training/`: separate UB and live keyboard/mouse
`*_windows_clean.jsonl` (same structure and order, no nulls, no IP),
`*_windows_normalized.jsonl` (per-source median/IQR scaling so UB and live can
be used together), `normalization_params.json` and `data_quality_report.json`
(windows per user). Live users are relabelled `L01`, `L02`, ... by sorted user
ID; the real ID stays in `user_id`.
