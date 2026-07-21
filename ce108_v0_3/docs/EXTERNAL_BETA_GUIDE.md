# CE108 External Beta Guide

## Purpose

This guide explains what must be prepared before giving CE108 to people outside the local development environment.

v0.4.1 is for controlled external beta testing. It is not a public commercial launch.

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

Teacher/operator testers should check:

- Whether the student daily loop is understandable without explanation.
- Whether sample-content disclaimers are visible enough.
- Whether error messages are understandable.
- Whether feedback is stored.

## Information To Tell Testers

Tell testers the following before sharing the URL:

```text
CE108 is currently a beta test version.
Included questions are original sample questions for operation verification.
This is not an official exam prediction service.
Do not enter private medical, school, payment, or personal information.
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
- Demo accounts and passwords are intentionally chosen for beta testing.
- Teacher/admin Streamlit screens are not publicly exposed.
- `/health` returns `0.4.1`.
- Mobile login succeeds.
- Feedback submission succeeds.

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
- Most common confusion points.
- Whether students understand that questions are samples.

## Stop Conditions

Pause the beta if:

- Login fails for multiple testers.
- Home shows `Failed to fetch`.
- Answer submission fails.
- Correct answer information appears before answering.
- Testers misunderstand sample content as official exam content.
- Data is lost after service restart.

## Next Step After Beta

After 3 to 5 testers complete the flow, summarize:

- What worked.
- What confused testers.
- What should be fixed before a larger class beta.
- Whether CE108 is ready for v0.4.2 or v0.5 planning.
