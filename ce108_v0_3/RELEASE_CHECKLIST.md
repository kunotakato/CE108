# CE108 v0.3 Release Checklist

Date: 2026-07-01
Release: v0.3.0-internal-alpha

## Environment
- [x] Python 3.12.13 installed.
- [x] Fresh virtual environment created at `.venv312`.
- [x] Dependencies installed from `requirements.txt`.
- [x] `data/ce108.db` deleted before initialization.
- [x] `python scripts/init_db.py` equivalent run with Python 3.12.

## Automated Verification
- [x] `python -m unittest discover -s tests -v` passed: 16 tests.
- [x] `python -m compileall app.py api.py ce108 scripts tests` passed.

## API Verification
- [x] FastAPI started with Python 3.12 venv.
- [x] `GET /health` returned 200.
- [x] Demo student login succeeded.
- [x] `GET /api/users/me` succeeded.
- [x] Question list and detail APIs succeeded.
- [x] Question detail API does not expose correct answer fields or explanations before answer.
- [x] Today’s study API generated a plan.
- [x] Diagnostic start API created a 30-question session.

## Streamlit Verification
- [x] Streamlit started with Python 3.12 venv.
- [x] Student home screen verified.
- [x] Teacher dashboard verified.
- [x] Admin dashboard verified.

## Release Hygiene
- [x] `data/*.db` is ignored by Git.
- [x] `.venv*/` is ignored by Git.
- [x] README commands match the verified local workflow.
- [x] Known limitations documented.
- [x] Acceptance report created.

## Completion Decision
- [x] v0.3 internal alpha is complete for local reproducible use.

