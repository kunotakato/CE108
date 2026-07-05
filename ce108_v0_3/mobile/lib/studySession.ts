"use client";

import type { SessionAnswer } from "./types";

const KEY = "ce108_mobile_today_session";

export function resetSession() {
  localStorage.setItem(KEY, JSON.stringify({ startedAt: Date.now(), answers: [] }));
}

export function addSessionAnswer(answer: SessionAnswer) {
  const current = getSession();
  const answers = current.answers.filter((item) => item.questionId !== answer.questionId);
  answers.push(answer);
  localStorage.setItem(KEY, JSON.stringify({ startedAt: current.startedAt, answers }));
}

export function getSession(): { startedAt: number; answers: SessionAnswer[] } {
  if (typeof window === "undefined") return { startedAt: Date.now(), answers: [] };
  const raw = localStorage.getItem(KEY);
  if (!raw) return { startedAt: Date.now(), answers: [] };
  try {
    const parsed = JSON.parse(raw) as { startedAt?: number; answers?: SessionAnswer[] };
    return { startedAt: parsed.startedAt ?? Date.now(), answers: parsed.answers ?? [] };
  } catch {
    return { startedAt: Date.now(), answers: [] };
  }
}
