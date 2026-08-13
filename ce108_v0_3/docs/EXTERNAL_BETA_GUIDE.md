# CE108 External Beta Guide

## Purpose

This guide explains what must be prepared before giving CE108 to people outside the local development environment.

v0.4.3 is for first-tester operations. It is not a public commercial launch.

## Who Can Test

Recommended first testers:

- 3 to 5 trusted students or colleagues.
- 1 teacher or domain expert who can review explanations.
- 1 administrator/operator who can check setup and feedback flow.

Do not invite a full class until the small beta checklist has passed.

## What Testers Should Try

Student testers should complete this flow:

1. Open the mobile URL.
2. Log in with a beta account.
3. Read the home screen.
4. Start today's five-question session.
5. Answer at least one question.
6. Confirm that explanation and review date appear.
7. Open the review queue.
8. Send feedback from the feedback screen.
9. Open the note AI screen with non-private study notes only.
10. Generate one note question and confirm the warning text is understandable.

Teacher/operator testers should check:

- Whether the student daily loop is understandable without explanation.
- Whether sample-content disclaimers are visible enough.
- Whether note AI warnings are visible enough.
- Whether error messages are understandable.
- Whether feedback is stored.

## Information To Tell Testers

Tell testers the following before sharing the URL:

```text
CE108 is currently a beta test version.
Included questions are original sample questions for operation verification.
This is not an official exam prediction service.
Do not enter patient, private medical, school-confidential, payment, or personal information.
Note AI questions are generated for review and may be wrong.
Please send usability feedback from the feedback screen after trying it.
```

## Must-Have Before Sharing The URL

- Hosted FastAPI URL works over HTTPS.
- Hosted mobile URL works over HTTPS.
- `CE108_APP_SECRET` is changed from the demo value.
- `CE108_CORS_ORIGINS` only includes intended frontend origins.
- `NEXT_PUBLIC_API_BASE_URL` points to the hosted API.
- SQLite database is on persistent storage.
- Database backup procedure is known.
- Tester student accounts are issued before sharing the mobile URL.
- Demo account autofill is disabled on the public mobile URL unless intentionally enabled.
- Teacher/admin Streamlit screens are not publicly exposed.
- `/health` returns `0.4.3`.
- Mobile login succeeds.
- Feedback submission succeeds.

## Creating The First Tester Account

Local or Render Shell:

```bash
python scripts/create_tester_account.py \
  --email beta1@example.com \
  --password replace-with-8-or-more-chars \
  --display-name 外部β1
```

Admin API:

```bash
curl -X POST "$API_URL/api/admin/tester-students" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"beta1@example.com","password":"replace-with-8-or-more-chars","display_name":"外部β1"}'
```

## Feedback Categories

The mobile app stores beta feedback with:

- Rating from 1 to 5.
- Category.
- Message.
- Page URL.
- User agent.
- User ID.
- Created timestamp.

Allowed categories:

- 使いやすさ
- 問題・解説
- 不具合
- 要望
- その他

## What To Measure

For the first beta, measure:

- Login success rate.
- Number of students who reach the home screen.
- Number of students who submit one answer.
- Number of feedback submissions.
- Whether the tester avoids entering private information into note AI.
- Most common confusion points.
- Whether students understand that questions are samples.

## Stop Conditions

Pause the beta if:

- Login fails for multiple testers.
- Home shows `Failed to fetch`.
- Answer submission fails.
- Correct answer information appears before answering.
- Testers misunderstand sample content as official exam content.
- A tester enters personal, patient, or school-confidential information into note AI.
- Data is lost after service restart.

## Next Step After Beta

After 3 to 5 testers complete the flow, summarize:

- What worked.
- What confused testers.
- What should be fixed before a larger class beta.
- Whether CE108 is ready for a paid pilot or v0.5 planning.
