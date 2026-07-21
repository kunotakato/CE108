"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { ErrorState } from "@/components/StateViews";
import { hasCompletedOnboarding, saveAuth } from "@/lib/auth";
import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("student@ce108.local");
  const [password, setPassword] = useState("demo1234");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await login(username, password);
      if (result.user.role !== "student") {
        setError("モバイル版は学生アカウントで利用してください。");
        return;
      }
      saveAuth(result.access_token, result.user);
      router.replace(hasCompletedOnboarding() ? "/home" : "/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "ログインできませんでした。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell title="ログイン" nav={false}>
      <section className="hero stack">
        <p className="eyebrow">Web Beta Prep v0.4.1</p>
        <h1>今日の5問を、スマホで続ける。</h1>
        <p className="lead">CE108 の学生向けモバイル学習画面です。外部β検証ではサンプル問題で操作感を確認できます。</p>
      </section>
      <form className="panel form" onSubmit={handleSubmit}>
        <label className="field">
          <span>メールアドレス</span>
          <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label className="field">
          <span>パスワード</span>
          <input
            autoComplete="current-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        <button className="primary-button" disabled={loading} type="submit">
          {loading ? "ログイン中" : "ログイン"}
        </button>
      </form>
      {error ? <ErrorState message={error} /> : null}
    </AppShell>
  );
}
