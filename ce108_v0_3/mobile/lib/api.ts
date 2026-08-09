import type {
  AnswerPayload,
  AnswerResult,
  DailyStatus,
  FeedbackPayload,
  DailyPlan,
  LearningSummary,
  LoginResponse,
  MasteryRow,
  NoteQuestion,
  Question,
  ReviewQueue,
  ScoreRecordPayload,
  StudyMode,
  StudyStrategy,
  StudentNote
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

type ApiOptions = {
  token?: string | null;
  method?: string;
  body?: unknown;
  form?: URLSearchParams;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

async function parseError(response: Response) {
  const text = await response.text();
  try {
    const json = JSON.parse(text) as { detail?: string };
    return json.detail || text || "通信に失敗しました。";
  } catch {
    return text || "通信に失敗しました。";
  }
}

export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers = new Headers();
  if (options.token) headers.set("Authorization", `Bearer ${options.token}`);
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
    headers.set("Content-Type", "application/x-www-form-urlencoded");
  } else if (options.body !== undefined) {
    body = JSON.stringify(options.body);
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    headers,
    body
  });
  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }
  return response.json() as Promise<T>;
}

export async function login(username: string, password: string) {
  const form = new URLSearchParams({ username, password });
  return apiFetch<LoginResponse>("/api/auth/login", { method: "POST", form });
}

export async function getToday(token: string) {
  return apiFetch<DailyPlan>("/api/study/today", { token });
}

export async function getFocusPlan(token: string, mode: StudyMode, count = 5) {
  return apiFetch<DailyPlan>(`/api/study/focus?mode=${mode}&count=${count}`, { token });
}

export async function getDailyStatus(token: string) {
  return apiFetch<DailyStatus>("/api/study/daily-status", { token });
}

export async function getReviewQueue(token: string, limit = 20) {
  return apiFetch<ReviewQueue>(`/api/study/reviews?limit=${limit}`, { token });
}

export async function getSummary(token: string) {
  return apiFetch<LearningSummary>("/api/study/summary", { token });
}

export async function getMastery(token: string, limit = 3) {
  return apiFetch<MasteryRow[]>(`/api/study/mastery?limit=${limit}`, { token });
}

export async function getStrategy(token: string) {
  return apiFetch<StudyStrategy>("/api/study/strategy", { token });
}

export async function saveTargetExamDate(token: string, target_exam_date: string) {
  return apiFetch<StudyStrategy>("/api/study/target-exam", {
    token,
    method: "POST",
    body: { target_exam_date }
  });
}

export async function addExamEvent(token: string, payload: { event_type: "mock" | "past_exam" | "real_exam"; title: string; event_date: string; memo?: string }) {
  return apiFetch<{ event_id: number }>("/api/study/exam-events", {
    token,
    method: "POST",
    body: payload
  });
}

export async function addScoreRecord(token: string, payload: ScoreRecordPayload) {
  return apiFetch<{ score_id: number }>("/api/study/scores", {
    token,
    method: "POST",
    body: payload
  });
}

export async function getNotes(token: string) {
  return apiFetch<StudentNote[]>("/api/notes", { token });
}

export async function createNote(token: string, payload: { title: string; content: string; source_type?: string }) {
  return apiFetch<{ note_id: number }>("/api/notes", {
    token,
    method: "POST",
    body: payload
  });
}

export async function generateNoteQuestions(token: string, noteId: number, count = 5) {
  return apiFetch<{ note_id: number; generated_count: number; questions: NoteQuestion[] }>(`/api/notes/${noteId}/generate`, {
    token,
    method: "POST",
    body: { count }
  });
}

export async function answerNoteQuestion(token: string, questionId: number, payload: { selected_code: string; confidence: string; response_time_seconds: number }) {
  return apiFetch<{ is_correct: boolean; question: NoteQuestion }>(`/api/note-questions/${questionId}/answer`, {
    token,
    method: "POST",
    body: payload
  });
}

export function assertQuestionSafe(question: Record<string, unknown>) {
  const forbidden = ["correct_codes", "is_correct", "numeric_answer", "explanation_short", "explanation_standard", "explanation_detailed"];
  for (const key of forbidden) {
    if (key in question) {
      throw new ApiError("回答前に正解情報を取得しました。画面表示を停止します。", 500);
    }
  }
  const choices = Array.isArray(question.choices) ? question.choices : [];
  if (choices.some((choice) => choice && typeof choice === "object" && ("is_correct" in choice || "explanation" in choice))) {
    throw new ApiError("回答前に選択肢の解説情報を取得しました。画面表示を停止します。", 500);
  }
}

export async function getQuestion(token: string, id: number) {
  const question = await apiFetch<Question>(`/api/questions/${id}`, { token });
  assertQuestionSafe(question as unknown as Record<string, unknown>);
  return question;
}

export async function submitAnswer(token: string, questionId: number, payload: AnswerPayload) {
  return apiFetch<AnswerResult>(`/api/questions/${questionId}/answer`, {
    token,
    method: "POST",
    body: payload
  });
}

export async function submitFeedback(token: string, payload: FeedbackPayload) {
  return apiFetch<{ feedback_id: number; status: "saved" }>("/api/beta/feedback", {
    token,
    method: "POST",
    body: payload
  });
}
