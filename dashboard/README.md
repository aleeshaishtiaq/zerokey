# ZeroKey Admin Console (Frontend POC)

High-fidelity prototype for **ZeroKey — Continuous Post-Login Authentication & Active Cyber Deception**.

## Run locally

```bash
npm install
npm run dev
```

Open the URL shown in the terminal (typically `http://localhost:5173`).

## Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router
- Recharts

All data is mock/local state — no backend required.

## Feasibility testing

This repository demonstrates a clickable, high-fidelity functional prototype. It validates the interface flow and local risk-analysis pipeline; it is not a full MVP and does not connect to a production API.

### What was run

- `npm run build` to verify the React, TypeScript, routing, charts, alert views, session investigation flow, and local data pipeline compile and bundle successfully.
- A local data check across the five sample sessions (`S-1042`, `S-1031`, `S-1055`, `S-1077`, and `S-1101`) and their behavioral analysis windows.
- A baseline risk experiment using 12 keyboard and mouse features per session, with Normal, Slight Deviation, and Significant Deviation states.
- Alert-flow checks for session start, session IP, IP change, risk score change, and suspicious activity.

### Evidence obtained

- Normal sessions with no deviations remain at the baseline score of `15`.
- A session with four slight deviations and one anomalous window produces a medium-range score of `43`, without being promoted to High Risk.
- High Risk requires at least three significant feature deviations, at least two anomalous windows, and sustained evidence across windows.
- S-1042 and S-1101 meet that combined-evidence rule; their scores are capped at `100`.
- An IP change is visible in Session Investigation as the new IP and is highlighted in red with a pulse animation.
- The Alerts page contains only the five requested alert types and no longer displays state, status, or action columns.

### What changed after testing

- Risk scoring moved from isolated feature reactions to an aggregate multi-feature and multi-window calculation.
- Slight deviations contribute a small amount but cannot independently create High Risk.
- The high-risk guard prevents one or two features from escalating a session without sustained evidence.
- Session reports use the same derived session score as the local risk experiment.
- The prototype now exposes the risk evidence through behavioral feature tables, analysis windows, session investigation, and the focused Alerts page.

### Feasibility conclusion

The prototype demonstrates that the intended workflow is technically feasible with local data: behavioral signals can be combined, threshold behavior can be tested deterministically, and the resulting risk explanation can be surfaced through a clickable admin workflow. Production feasibility still requires a real telemetry API, persisted event history, calibrated thresholds, authentication, and security/privacy validation.
