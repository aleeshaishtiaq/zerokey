# Vercel Environment Checklist

The current Vercel configuration deploys the FastAPI API through
`src/api/main.py`. The existing CD workflow does not deploy the portal or
dashboard. Do not treat a successful API deployment as a complete web demo.

## Vercel project configuration

Configure these variables manually in the API Vercel project:

| Variable | Environment | Type | Source |
| --- | --- | --- | --- |
| `AUTH0_DOMAIN` | Production, Preview, Development as needed | Config | Auth0 tenant domain |
| `AUTH0_AUDIENCE` | Production, Preview, Development as needed | Config | Auth0 API identifier |
| `AUTH0_ALLOWED_SUBJECTS` | Production, Preview, Development as needed | Config/allowlist | Approved Auth0 subject IDs |
| `CORS_ALLOWED_ORIGINS` | Production, Preview, Development as needed | Config | Exact deployed portal/dashboard origins and approved extension origin |
| `TELEMETRY_LOG_PATH` | Only if intentionally configured | Config | Persistent storage path; Vercel serverless storage is not durable |

The API does not require a Vercel secret for runtime Auth0 validation. Never
put Auth0 Management API secrets or client secrets in these files.

If a durable JSONL log is required in production, verify the storage design
first. The current API writes a local JSONL path and Vercel serverless filesystems
are not a durable database.

## GitHub Actions secrets

The CD workflow reads these GitHub Actions secrets:

| Secret | Used by |
| --- | --- |
| `VERCEL_TOKEN` | Vercel CLI authentication |
| `VERCEL_ORG_ID` | Vercel project scope |
| `VERCEL_PROJECT_ID` | Vercel API project scope |

They must be configured in GitHub Actions Secrets and must not appear in
source, documentation, pull requests, or logs.

## Deployment conditions

CD runs only when:

1. CI completes successfully.
2. The workflow run was caused by a push.
3. The pushed branch is `develop`.

Feature-branch pull requests receive CI checks but are not deployed by the CD
workflow. After changing Vercel environment variables, trigger a new eligible
deployment and verify `/api/health` and authenticated API access separately.