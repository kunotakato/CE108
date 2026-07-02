# CE108 v0.4 Plan: Daily Learning Beta

## 1. Purpose

CE108 v0.4 is the first beta-oriented release after the v0.3 local MVP and v0.3.5 mobile alpha.

The goal is not to add many unrelated features. The goal is to make CE108 feel useful enough that students want to open it every day, while teachers and administrators can support that learning safely.

## 2. Release Theme

Daily Learning Beta

Students should be able to:

- Know exactly what to do today.
- Finish a short learning session on a smartphone.
- Understand why an answer was right or wrong.
- See progress and weak areas clearly.
- Come back tomorrow with a reason to continue.

Teachers should be able to:

- See which assigned students need support.
- Understand weak areas at a glance.
- Check whether students are continuing.

Administrators should be able to:

- Manage question quality before publication.
- Avoid publishing problems with unclear rights or incomplete explanations.
- Keep sample content clearly separated from official past exam content.

## 3. Current Baseline

v0.3 includes:

- Student login.
- 30-question diagnostic.
- Daily recommended questions.
- Single choice, true/false, and numeric questions.
- Answer history, confidence, response time, correctness, explanations, mastery updates, and review scheduling.
- Teacher student list, assignments, results, and CSV export.
- Admin question creation, CSV import, permission status, approval, unpublish, and audit logs.
- FastAPI endpoints for login, users, questions, answers, daily study, diagnostics, teacher, and admin workflows.
- LINE webhook signature verification, tester request storage, and LIFF HTML placeholder.

v0.3.5 adds:

- Student mobile Next.js app.
- Login, onboarding, home, today's 5 questions, post-answer explanation, result, and mastery screens.
- PWA manifest.
- Mobile width checks for 320px, 375px, 390px, and 430px.
- Frontend guard against exposing answer information before submission.

## 4. v0.4 Scope

### 4.1 Student Daily Learning

Implement a more rewarding daily study loop:

- Daily streak count.
- Today's completion state.
- Weekly completion summary.
- Missed-day recovery message.
- Resume unfinished daily session.
- Tomorrow preview after finishing today's questions.
- Clear next action on the mobile home screen.

### 4.2 Student Review Experience

Improve review behavior without changing the database technology:

- Review queue screen for due items.
- Review status labels: due today, overdue, upcoming.
- Review completion state.
- Weak-area callout based on mastery data.
- "Why this is recommended" reason display.

### 4.3 Student Explanation Experience

Make explanations more useful for self-study:

- Show explanation sections as:
  - Key point.
  - Why the correct answer is correct.
  - Why common mistakes are wrong.
  - Memory tip.
- For numeric questions, show formula and calculation steps when available.
- Keep answer and explanation hidden before submission.
- Preserve existing sample-content disclaimers.

### 4.4 Teacher Support View

Make teachers able to identify support needs quickly:

- At-risk student list.
- Student continuation status.
- Student weak-topic summary.
- Assignment completion status.
- Class-level weak-topic ranking.
- CSV export for the new summary fields.

### 4.5 Admin Quality Control

Strengthen publication safety:

- Question quality checklist.
- Explanation completeness check.
- Permission status warning.
- CSV import preview before final insert.
- Duplicate-looking question detection by simple text similarity.
- Admin dashboard for draft, checking, approved, and unpublished counts.

### 4.6 Documentation and Release Operations

Prepare v0.4 as a reproducible beta:

- Update README for v0.4 workflows.
- Add v0.4 acceptance report.
- Add v0.4 known limitations.
- Add mobile manual test checklist.
- Add release checklist.
- Keep setup reproducible from `requirements.txt` and `mobile/package-lock.json`.

## 5. Explicitly Out of Scope for v0.4

Do not implement the following in v0.4:

- PostgreSQL migration.
- Full production multi-tenant school management.
- Paid billing.
- Official national exam past-question ingestion.
- AI-generated question publication.
- Required external AI API dependency.
- Full LINE Login production connection.
- LINE Push notification production operation.
- Replacement of Streamlit teacher/admin screens with React.
- Large database redesign unless a small migration is essential for v0.4 acceptance.

## 6. Proposed User Value

### Students

Students get a clear daily routine:

- Open app.
- See today's target.
- Solve 5 questions.
- Understand mistakes.
- See progress.
- Know what to review next.

This makes CE108 feel less like a question database and more like a daily study partner.

### Teachers

Teachers get signals for intervention:

- Who stopped studying.
- Who is weak in which topic.
- Who has incomplete assignments.
- Which topics are weak across the class.

This makes CE108 useful in actual class support.

### Administrators

Administrators get safer publishing:

- Question status is visible.
- Explanation quality is checked.
- Rights status is harder to miss.
- CSV import is less risky.

This makes CE108 safer to prepare for beta testing.

## 7. Acceptance Criteria

v0.4 is complete only when all items below pass.

### Student

- A demo student can open the mobile app and see today's learning status.
- A student can resume an unfinished daily session.
- A student can finish today's questions and see completion feedback.
- A student can see streak and weekly completion summary.
- A student can open a review queue.
- Due and overdue review items are clearly shown.
- Explanations remain hidden before answer submission.
- Post-answer explanations show structured sections when data exists.

### Teacher

- A demo teacher can see assigned students only.
- A teacher can see at-risk students.
- A teacher can see weak-topic summaries.
- A teacher can see assignment completion status.
- A teacher can export updated summary CSV.
- A teacher cannot access unassigned students.

### Admin

- A demo admin can see question quality status.
- An admin can preview CSV import results before insertion.
- An admin receives warnings for incomplete explanations.
- An admin cannot publish rights-unconfirmed questions.
- Admin actions continue to be recorded in audit logs.

### API

- `/health` returns 200.
- Existing v0.3 and v0.3.5 endpoints remain backward compatible.
- New v0.4 endpoints have role-based access control.
- Student APIs do not expose correct answers before submission.
- Error responses are understandable.

### Mobile

- No horizontal scroll at 320px, 375px, 390px, and 430px.
- Main student flows work on mobile viewport.
- Loading, empty, and error states exist for new screens.
- Primary daily action remains visible without hunting through menus.

## 8. Test Plan

### Python

- Existing unittest suite must pass.
- Add tests for:
  - Daily completion state.
  - Resume daily session.
  - Review queue generation.
  - Teacher at-risk student access control.
  - Admin quality checklist.
  - CSV preview validation.
  - Answer-before-submit safety.

### Mobile

- `npm run typecheck`
- `npm run lint`
- `npm test`
- `npm run build`
- `npm run test:e2e`

Add E2E scenarios for:

- Login to daily completion.
- Resume unfinished daily session.
- Review queue open and complete.
- Streak and weekly summary display.
- API error retry.
- Mobile widths: 320, 375, 390, 430.

## 9. Release Checklist

- All Python tests pass.
- All mobile tests pass.
- FastAPI starts locally.
- Streamlit starts locally.
- Mobile app starts locally.
- `/health` returns 200.
- Demo student login works.
- Demo teacher login works.
- Demo admin login works.
- No `data/*.db` is tracked.
- No `.env` is tracked.
- No `.DS_Store` is tracked.
- No official past exam text is added.
- README and docs match actual commands.
- v0.4 tag is created only after all checks pass.

## 10. Suggested Implementation Order

1. Create `feature/v0.4-daily-learning-beta`.
2. Add or update service functions for daily completion and review queue.
3. Add FastAPI endpoints for v0.4 student daily status and review queue.
4. Add tests for service and API behavior.
5. Update mobile home, result, review, and mastery screens.
6. Add mobile unit and E2E tests.
7. Add teacher support summaries.
8. Add admin quality checklist and CSV preview.
9. Update README and release docs.
10. Run full verification and fix regressions.

## 11. Open Questions

- Should v0.4 include a small SQLite migration, or should it reuse existing tables as much as possible?
- Should streak be stored server-side or derived from `answer_history`?
- Should teacher at-risk logic be rule-based only, or configurable by the teacher?
- Should structured explanations require new columns, or can v0.4 derive sections from existing explanation fields?
- Should review queue completion update `review_schedules.status`, or remain implicit through answer history?

## 12. Recommended Decision

For v0.4, prefer conservative implementation:

- Derive streak and weekly summary from existing answer history first.
- Reuse existing review schedules.
- Add minimal columns only if a behavior cannot be represented cleanly.
- Keep AI and LINE production features out of scope.
- Focus on daily student usefulness, teacher support visibility, and admin publishing safety.
