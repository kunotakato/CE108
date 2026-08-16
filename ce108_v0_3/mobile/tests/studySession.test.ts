import { beforeEach, describe, expect, it } from "vitest";
import { addSessionAnswer, ensureSession, getSession, resetSession } from "@/lib/studySession";

describe("study session storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("separates sessions by plan key and removes legacy answers", () => {
    localStorage.setItem(
      "ce108_mobile_today_session",
      JSON.stringify({
        startedAt: Date.now() - 3 * 24 * 60 * 60 * 1000,
        answers: [{ questionId: 99, isCorrect: true, reviewDate: "2026-08-16", seconds: 10 }]
      }),
    );

    const session = ensureSession("daily:2026-08-16:1:1-2-3-4-5");

    expect(session.answers).toHaveLength(0);
    expect(session.sessionKey).toBe("daily:2026-08-16:1:1-2-3-4-5");
  });

  it("deduplicates answers inside the active session", () => {
    const key = "daily:2026-08-16:1:1-2-3-4-5";
    resetSession(key);

    addSessionAnswer(key, { questionId: 1, isCorrect: false, reviewDate: "2026-08-17", seconds: 20 });
    addSessionAnswer(key, { questionId: 1, isCorrect: true, reviewDate: "2026-08-30", seconds: 15 });

    const session = getSession(key);
    expect(session.answers).toHaveLength(1);
    expect(session.answers[0].isCorrect).toBe(true);
    expect(session.answers[0].seconds).toBe(15);
  });
});
