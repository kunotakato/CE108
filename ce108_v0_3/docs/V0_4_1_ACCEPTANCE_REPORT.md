# CE108 v0.4.1 Acceptance Report

## Release

CE108 v0.4.1 Web Deployment Preparation

## Summary

v0.4.1 prepares CE108 for external URL beta testing.

This release keeps the v0.4 feature set and architecture, then adds deployment-oriented configuration and documentation so the mobile app can call a hosted FastAPI service safely.

## Implemented

- FastAPI version updated to `0.4.1`.
- `/health` returns `0.4.1`.
- CORS origins can be configured with `CE108_CORS_ORIGINS`.
- Local CORS defaults remain available when `CE108_CORS_ORIGINS` is empty.
- Mobile package version updated to `0.4.1`.
- Mobile environment example explains local and deployed API URLs.
- FastAPI `.env.example` documents web deployment variables.
- Deployment plan added in `docs/DEPLOYMENT_PLAN.md`.
- External beta guide added in `docs/EXTERNAL_BETA_GUIDE.md`.
- Authenticated beta feedback API added at `/api/beta/feedback`.
- Mobile feedback screen added at `/feedback`.
- Mobile home links to the feedback screen.
- Concurrent daily plan generation fix included from v0.4 stabilization.

## Validation

The following checks passed locally:

```bash
python -m unittest discover -s tests -v
python -m compileall app.py api.py ce108 scripts tests
python scripts/init_db.py
cd mobile && npm run typecheck
cd mobile && npm run lint
cd mobile && npm test
cd mobile && npm run build
```

Results:

- Python unittest: 29 tests passed.
- Python compileall: passed.
- Database initialization: passed.
- Mobile unit tests: 6 tests passed.
- Mobile typecheck: passed.
- Mobile lint: passed.
- Mobile build: passed.
- `/health`: returned `{"status":"ok","version":"0.4.1"}`.
- `/api/beta/feedback`: returned `{"status":"saved"}`.

Manual checks:

- FastAPI `/health` returns `0.4.1`.
- Mobile local login succeeds with FastAPI running.
- Home loads without `Failed to fetch`.
- Today's five-question screen loads.
- A submitted answer displays explanation and review date.
- Feedback submission stores tester feedback.

## Acceptance Status

Local validation passed. Deployment target selection and hosted URL validation remain pending.

## Remaining Limitations

- No production deployment has been created by this release.
- SQLite remains the beta database.
- Teacher/admin Streamlit screens are not prepared for public exposure.
- LINE production connection remains out of scope.
- Billing and subscription features remain out of scope.
- Demo accounts must not be used for broad public launch.
