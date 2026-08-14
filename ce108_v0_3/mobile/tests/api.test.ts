import { describe, expect, it, vi } from "vitest";
import { assertQuestionSafe, extractNoteText, getQuestion, login, submitFeedback } from "@/lib/api";

describe("api client", () => {
  it("posts demo login as form data", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ access_token: "token", token_type: "bearer", user: { id: 1, role: "student" } })
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await login("student@ce108.local", "demo1234");

    expect(response.access_token).toBe("token");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[0][1].body.toString()).toContain("username=student%40ce108.local");
    vi.unstubAllGlobals();
  });

  it("rejects answer details before response", () => {
    expect(() =>
      assertQuestionSafe({
        id: 1,
        question_text: "sample",
        correct_codes: ["1"],
        choices: [{ choice_code: "1", choice_text: "A" }]
      })
    ).toThrow("正解情報");
  });

  it("rejects choice explanations before response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: 1,
          question_type: "single",
          question_text: "sample",
          choices: [{ choice_code: "1", choice_text: "A", explanation: "hidden" }]
        })
      })
    );

    await expect(getQuestion("token", 1)).rejects.toThrow("選択肢の解説情報");
    vi.unstubAllGlobals();
  });

  it("posts beta feedback", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ feedback_id: 1, status: "saved" })
    });
    vi.stubGlobal("fetch", fetchMock);

    const response = await submitFeedback("token", { rating: 5, category: "使いやすさ", message: "続けられそうです。" });

    expect(response.status).toBe("saved");
    expect(fetchMock.mock.calls[0][0]).toContain("/api/beta/feedback");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[0][1].headers.get("Authorization")).toBe("Bearer token");
    vi.unstubAllGlobals();
  });

  it("uploads note files as form data", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ filename: "memo.txt", content_type: "text/plain", source_type: "uploaded_text", text: "透析メモの本文です。" })
    });
    vi.stubGlobal("fetch", fetchMock);

    const file = new File(["透析メモの本文です。"], "memo.txt", { type: "text/plain" });
    const response = await extractNoteText("token", file);

    expect(response.source_type).toBe("uploaded_text");
    expect(fetchMock.mock.calls[0][0]).toContain("/api/notes/extract");
    expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    expect(fetchMock.mock.calls[0][1].headers.get("Authorization")).toBe("Bearer token");
    expect(fetchMock.mock.calls[0][1].headers.get("Content-Type")).toBeNull();
    expect(fetchMock.mock.calls[0][1].body).toBeInstanceOf(FormData);
    vi.unstubAllGlobals();
  });
});
