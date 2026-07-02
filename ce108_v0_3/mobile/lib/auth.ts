"use client";

import type { User } from "./types";

const TOKEN_KEY = "ce108_mobile_token";
const USER_KEY = "ce108_mobile_user";

export function saveAuth(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getToken() {
  return typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function hasCompletedOnboarding() {
  return typeof window !== "undefined" && localStorage.getItem("ce108_mobile_onboarding") === "done";
}

export function completeOnboarding(settings: Record<string, string>) {
  localStorage.setItem("ce108_mobile_onboarding", "done");
  localStorage.setItem("ce108_mobile_onboarding_settings", JSON.stringify(settings));
}
