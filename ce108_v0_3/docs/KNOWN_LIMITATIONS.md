# Known Limitations

CE108 v0.3 is an internal alpha intended for local, reproducible MVP verification.

## Content
- Included questions are CE108 original samples for functional verification.
- Official national exam question text is not included.
- Medical and engineering explanations are sample MVP content and require expert review before production use.

## Authentication And Security
- Demo accounts use the shared password `demo1234`.
- Access tokens are locally signed. Set a strong `CE108_APP_SECRET` outside local demo use.
- CORS is limited to local Streamlit origins, but production origin policy is not finalized.
- School-wide production access control is not finalized.

## LINE And LIFF
- LINE webhook signature verification is implemented.
- “テスター希望” message intake is stored locally.
- LIFF HTML scaffold exists.
- LINE Login, Push Message, LIFF access token verification, and production webhook delivery are not connected in v0.3.

## Data And Operations
- SQLite is used for local MVP operation.
- `data/*.db` is intentionally ignored by Git and must be generated with `python scripts/init_db.py`.
- No schema migration framework is included.
- PostgreSQL migration is deferred to a later version.

## Scope Deferred To v0.4+
- Production deployment hardening.
- Multi-school operational policies.
- Expert-reviewed content workflow.
- Official question rights management beyond stored permission status.
- AI-generated similar question workflow.

