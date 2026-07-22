# CE108 v0.4.1 Deployment Plan

## Purpose

v0.4.1 is a web deployment preparation release.

The goal is not full production commercialization. The goal is to make CE108 ready to be shared through external URLs for small beta validation while keeping the v0.4 architecture intact.

## Target Architecture

```text
Student mobile app
  Next.js
  Deployed to Vercel or an equivalent static/Node hosting service

FastAPI
  Python 3.12
  Deployed to Render, Railway, Fly.io, VPS, or another service with persistent storage

Database
  SQLite for v0.4.1 beta
  Stored on a persistent disk attached to the FastAPI service

Teacher/Admin
  Streamlit remains local or separately protected
  Do not expose publicly without access control
```

## Required Environment Variables

### FastAPI

```text
CE108_APP_SECRET=<long-random-secret>
CE108_DB_PATH=/var/lib/ce108/ce108.db
CE108_TOKEN_TTL_SECONDS=43200
CE108_CORS_ORIGINS=https://your-mobile-app.example.com
PUBLIC_BASE_URL=https://your-api.example.com
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=
LIFF_ID=
```

### Mobile

```text
NEXT_PUBLIC_API_BASE_URL=https://your-api.example.com
```

## FastAPI Deployment Steps

1. Create a Python 3.12 service.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Attach persistent storage for SQLite.
4. Set `CE108_DB_PATH` to a path on that persistent storage.
5. Initialize the database:

```bash
python scripts/init_db.py
```

6. Start the API:

```bash
uvicorn api:app --host 0.0.0.0 --port $PORT
```

7. Confirm health:

```text
https://your-api.example.com/health
```

Expected response:

```json
{"status":"ok","version":"0.4.1"}
```

## Mobile Deployment Steps

1. Deploy `ce108_v0_3/mobile` as the Next.js project root.
2. Set `NEXT_PUBLIC_API_BASE_URL` to the deployed FastAPI URL.
3. Build with:

```bash
npm install
npm run build
```

4. Open:

```text
https://your-mobile-app.example.com/login
```

5. Confirm demo login only in a controlled beta environment:

```text
student@ce108.local
demo1234
```

## CORS

FastAPI reads `CE108_CORS_ORIGINS` as a comma-separated list.

Example:

```text
CE108_CORS_ORIGINS=https://ce108-mobile.vercel.app,https://ce108-admin.example.com
```

Do not use wildcard CORS for shared beta or production use.

## Render Deployment

Use the repository-level `render.yaml` for a concrete Render setup.

Details:

```text
docs/RENDER_DEPLOYMENT.md
```

Important:

- Render web services must bind to `0.0.0.0:$PORT`.
- `ce108-api` should use a persistent disk if SQLite data must survive restarts.
- Render Free web services do not preserve local SQLite files.
- Deploy or redeploy `ce108-mobile` after setting `NEXT_PUBLIC_API_BASE_URL`.

## Web Beta Acceptance Checks

- `/health` returns `0.4.1`.
- Mobile login succeeds from the deployed mobile URL.
- `/api/users/me` succeeds after login.
- Home loads without `Failed to fetch`.
- Today's five-question screen loads.
- At least one answer can be submitted.
- Explanation and review date appear after submission.
- Review queue loads.
- Feedback screen loads.
- Feedback submission returns `status: saved`.
- CORS only allows intended origins.
- SQLite database survives service restart.

## External Tester Readiness

Before sending the URL to anyone outside development, prepare:

- A short beta explanation.
- A tester account policy.
- A feedback collection path.
- A known contact route for urgent issues.
- A stop rule if login, answer submission, or data persistence fails.

Use `docs/EXTERNAL_BETA_GUIDE.md` as the tester-readiness checklist.

## Security Notes

- Replace the demo secret before any shared deployment.
- Do not expose Streamlit teacher/admin screens publicly without authentication controls.
- Do not use official national exam text unless rights are confirmed.
- Treat included content as sample content until expert review is complete.
- Back up the SQLite database before and after beta testing sessions.
- Do not ask beta testers to enter private medical, school, payment, or personal information.

## Out Of Scope

- PostgreSQL migration.
- Paid billing.
- Full LINE production connection.
- Production school tenant management.
- Official past-question ingestion.
- React replacement for teacher/admin screens.
