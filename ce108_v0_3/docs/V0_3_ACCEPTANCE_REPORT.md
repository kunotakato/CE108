# CE108 v0.3 Acceptance Report

Date: 2026-07-01
Release candidate: v0.3.0-internal-alpha
Python: 3.12.13

## Summary

CE108 v0.3 has passed the release acceptance checks for a local, reproducible internal alpha.

## Environment Verification

- Created a fresh Python 3.12 virtual environment: `.venv312`.
- Installed dependencies from `requirements.txt`.
- Deleted `data/ce108.db` before initialization.
- Reinitialized the SQLite database with `python scripts/init_db.py` under Python 3.12.

## Automated Tests

Command:

```bash
.venv312/bin/python -m unittest discover -s tests -v
```

Result: passed.

Coverage confirmed by tests:
- Demo login.
- Invalid login.
- 30-question diagnostic generation.
- Diagnostic question uniqueness.
- Diagnostic duplicate-answer rejection.
- Answer persistence.
- Correctness judgement.
- Numeric tolerance.
- Mastery update.
- Review date scheduling.
- Today’s study plan generation.
- Unconfirmed rights publication rejection.
- Student access denial to admin API.
- Teacher access denial for unassigned student.
- Answer-before API response does not expose correct answer fields or explanations.

## Compile Check

Command:

```bash
.venv312/bin/python -m compileall app.py api.py ce108 scripts tests
```

Result: passed.

## FastAPI Verification

Command:

```bash
.venv312/bin/uvicorn api:app --host 127.0.0.1 --port 8000
```

Verified:
- `GET /health`: 200 OK.
- `POST /api/auth/login`: demo student login succeeded.
- `GET /api/users/me`: returned current student profile.
- `GET /api/questions`: returned published sample questions.
- `GET /api/questions/1`: returned question and choices without correct answer fields or explanations.
- `GET /api/study/today`: generated today’s study plan.
- `POST /api/diagnostics/start`: created an in-progress diagnostic session.

## Streamlit Verification

Command:

```bash
.venv312/bin/streamlit run app.py --server.headless true --server.port 8503
```

Verified:
- Student home screen.
- Teacher dashboard.
- Admin dashboard.

## Git Hygiene

- `data/*.db` is ignored.
- `.venv*/` is ignored.
- `data/ce108.db` is treated as a generated local database, not a release source artifact.

## Acceptance Decision

Accepted as CE108 v0.3 internal alpha.

