# Past Question Import Policy

## Purpose

CE108 can track official past-question sources, but should not publish copied past-question text or third-party explanations until rights are confirmed.

## Current Decision

Do not import question text, choices, or explanations from third-party commentary sites into the public CE108 database.

Reasons:

- Third-party explanations are independently authored content.
- The linked commentary site presents protected content and an all-rights-reserved notice.
- CE108 already has rights-state controls, so past-question data should stay unpublished until permissions are clear.

## Safe Import States

Use these states for official past-question work:

```text
source_type=official_past_exam
permission_status=checking
status=draft
```

Only change to a public state when the content can be used:

```text
permission_status=permission_confirmed
status=published
```

## Public Beta Alternative

To increase the number of usable questions now, create CE108 original practice questions that are aligned with past-exam topics but do not copy:

- past-question wording
- choice wording
- third-party commentary
- third-party explanation structure

Use:

```text
source_type=original
permission_status=internal_sample
status=draft
```

Then review and publish through the admin workflow.

## Operational Workflow

1. Register official source metadata in `data/past_question_sources_39.csv`.
2. Draft original CE108 questions in CSV batches.
3. Import batches through admin CSV import.
4. Review explanations and topic mapping.
5. Publish only after quality review.
6. Keep official-past-question copies in draft until rights are confirmed.

## Notes For v0.4.1

The v0.4.1 public beta should use original sample questions. Exact national exam past-question ingestion remains a rights-review task.
