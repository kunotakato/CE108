"use client";

import type { SessionAnswer } from "./types";

const KEY = "ce108_mobile_today_session";
const MAX_SESSION_MS = 12 * 60 * 60 * 1000;

export type StudySession = {
  sessionKey: string;
  startedAt: number;
  answers: SessionAnswer[];
};

function fallbackSession(sessionKey = "unknown"): StudySession {
  return { sessionKey, startedAt: Date.now(), answers: [] };
}

function isValidStartedAt(startedAt: number) {
  const now = Date.now();
  return Number.isFinite(startedAt) && startedAt > 0 && startedAt <= now && now - startedAt <= MAX_SESSION_MS;
}

export function resetSession(sessionKey = "unknown") {
  const session = fallbackSession(sessionKey);
  localStorage.setItem(KEY, JSON.stringify(session));
  return session;
}

export function ensureSession(sessionKey: string) {
  const current = getSession(sessionKey);
  if (current.sessionKey !== sessionKey || !isValidStartedAt(current.startedAt)) {
    return resetSession(sessionKey);
  }
  return current;
}

export function addSessionAnswer(sessionKey: string, answer: SessionAnswer) {
  const current = ensureSession(sessionKey);
  const answers = current.answers.filter((item) => item.questionId !== answer.questionId);
  answers.push(answer);
  localStorage.setItem(KEY, JSON.stringify({ sessionKey, startedAt: current.startedAt, answers }));
}

export function getSession(sessionKey = "unknown"): StudySession {
  if (typeof window === "undefined") return fallbackSession(sessionKey);
  const raw = localStorage.getItem(KEY);
  if (!raw) return fallbackSession(sessionKey);
  try {
    const parsed = JSON.parse(raw) as { sessionKey?: string; startedAt?: number; answers?: SessionAnswer[] };
    if (!parsed.sessionKey || !isValidStartedAt(parsed.startedAt ?? 0)) {
      return fallbackSession(sessionKey);
    }
    return {
      sessionKey: parsed.sessionKey,
      startedAt: parsed.startedAt as number,
      answers: parsed.answers ?? []
    };
  } catch {
    return fallbackSession(sessionKey);
  }
}
