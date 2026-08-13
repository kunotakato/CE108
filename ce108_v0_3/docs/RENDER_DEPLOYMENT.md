# CE108 Render Deployment

## Purpose

This document is the concrete Render deployment guide for CE108 v0.4.3.

Use this when you want external beta testers to access CE108 from public URLs instead of `127.0.0.1`.

## Important Render Constraint

Render Free web services have ephemeral filesystems. Local files such as SQLite databases are lost when a free service restarts, redeploys, or spins down.

For CE108 with SQLite, use one of these options:

- Recommended beta: paid `starter` FastAPI service with a persistent disk.
- Short smoke test only: free FastAPI service with temporary SQLite, knowing data can disappear.
- Later production: migrate from SQLite to PostgreSQL.

The included `render.yaml` uses a persistent disk for `ce108-api`, which requires a paid service plan.

## Services

The repository root contains `render.yaml`.

It defines:

- `ce108-api`
  - Runtime: Python
  - Root directory: `ce108_v0_3`
  - Build command: `pip install -r requirements.txt`
  - Start command: `python scripts/init_db.py && uvicorn api:app --host 0.0.0.0 --port $PORT`
  - Health check: `/health`
  - SQLite path: `/var/data/ce108.db`

- `ce108-mobile`
  - Runtime: Node
  - Root directory: `ce108_v0_3/mobile`
  - Build command: `npm install && npm run build`
  - Start command: `npm run start -- -H 0.0.0.0 -p $PORT`

## Deployment Steps

1. Push this branch to GitHub.

```bash
git push -u origin feature/v0.4.1-web-deployment-prep
```

2. Open Render.

```text
https://dashboard.render.com/
```

3. Create a new Blueprint from the GitHub repository.

Repository:

```text
https://github.com/kunotakato/CE108
```

Blueprint file:

```text
render.yaml
```

4. During Blueprint setup, enter required environment values.

For `ce108-api`:

```text
CE108_CORS_ORIGINS=https://YOUR-MOBILE-SERVICE.onrender.com
PUBLIC_BASE_URL=https://YOUR-API-SERVICE.onrender.com
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=
LIFF_ID=
```

For `ce108-mobile`:

```text
NEXT_PUBLIC_API_BASE_URL=https://YOUR-API-SERVICE.onrender.com
```

5. Deploy `ce108-api` first.

Confirm:

```text
https://YOUR-API-SERVICE.onrender.com/health
```

Expected:

```json
{"status":"ok","version":"0.4.3"}
```

6. Deploy or redeploy `ce108-mobile` after `NEXT_PUBLIC_API_BASE_URL` is set.

Open:

```text
https://YOUR-MOBILE-SERVICE.onrender.com/login
```

7. Confirm the beta flow.

- Login.
- Home loads without `Failed to fetch`.
- Today's five-question screen loads.
- Submit at least one answer.
- Explanation and review date appear.
- Review queue loads.
- Feedback screen submits successfully.

## Demo Account

Use only for controlled beta:

```text
student@ce108.local
demo1234
```

Do not use this account for a broad public launch.

## Manual Render Setup Without Blueprint

If you do not use Blueprint, create these services manually.

### FastAPI Web Service

```text
Name: ce108-api
Runtime: Python
Root Directory: ce108_v0_3
Build Command: pip install -r requirements.txt
Start Command: python scripts/init_db.py && uvicorn api:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
Plan: Starter or higher if using SQLite persistence
Disk Mount Path: /var/data
Disk Size: 1 GB
```

Environment:

```text
PYTHON_VERSION=3.12.13
CE108_APP_SECRET=<long random secret>
CE108_DB_PATH=/var/data/ce108.db
CE108_TOKEN_TTL_SECONDS=43200
CE108_CORS_ORIGINS=https://YOUR-MOBILE-SERVICE.onrender.com
PUBLIC_BASE_URL=https://YOUR-API-SERVICE.onrender.com
```

### Mobile Web Service

```text
Name: ce108-mobile
Runtime: Node
Root Directory: ce108_v0_3/mobile
Build Command: npm install && npm run build
Start Command: npm run start -- -H 0.0.0.0 -p $PORT
Plan: Free is acceptable for beta frontend
```

Environment:

```text
NODE_VERSION=22
NEXT_PUBLIC_API_BASE_URL=https://YOUR-API-SERVICE.onrender.com
```

## Troubleshooting

### `/health` returns Not Found

Open:

```text
https://YOUR-API-SERVICE.onrender.com/health
```

The root path `/` is not the health endpoint.

### Mobile shows `Failed to fetch`

Check:

- `NEXT_PUBLIC_API_BASE_URL` points to the API service URL.
- `CE108_CORS_ORIGINS` includes the mobile service URL.
- The API service is awake and `/health` returns `0.4.3`.
- Mobile was rebuilt after setting `NEXT_PUBLIC_API_BASE_URL`.

### Data disappears

Check whether `ce108-api` is on a free plan. Free web services do not preserve SQLite files. Use a paid service with a persistent disk or migrate to PostgreSQL later.

## First External Beta Checklist

Before sending the URL:

- API and mobile URLs are both HTTPS.
- `/health` returns `0.4.3`.
- Demo login works.
- Home loads.
- Answer submission works.
- Feedback submission works.
- Testers are told this is a sample-content beta, not an official exam predictor.
