"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { getMastery, getSummary, getToday } from "@/lib/api";
import { getStoredUser, getToken } from "@/lib/auth";
import type { DailyPlan, LearningSummary, MasteryRow, User } from "@/lib/types";

export default function HomePage() {
  const [user, setUser] = useState<User | null>(null);
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [summary, setSummary] = useState<LearningSummary | null>(null);
  const [mastery, setMastery] = useState<MasteryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    const token = getToken();
    setUser(getStoredUser());
    if (!token) {
      setError("ログイン情報が見つかりません。ログインし直してください。");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [today, learning, weak] = await Promise.all([getToday(token), getSummary(token), getMastery(token, 3)]);
      setPlan(today);
      setSummary(learning);
      setMastery(weak);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ホームを読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <AppShell title="ホーム"><LoadingState /></AppShell>;

  if (error) {
    return (
      <AppShell title="ホーム">
        <ErrorState message={error} onRetry={load} />
        <Link className="link-button" href="/login">ログインへ戻る</Link>
      </AppShell>
    );
  }

  if (!plan) {
    return (
      <AppShell title="ホーム">
        <EmptyState message="今日の問題はまだ作成されていません。" />
      </AppShell>
    );
  }

  const completed = plan.items.filter((item) => item.completed).length;
  const nextWeak = mastery[0];

  return (
    <AppShell title="ホーム">
      <section className="hero stack">
        <p className="eyebrow">{user?.display_name || "学生"}さんの今日</p>
        <h1>5問だけ進めましょう。</h1>
        <p className="lead">{plan.estimated_minutes}分目安。完了済み {completed}/{plan.items.length} 問。</p>
        <Link className="primary-button" href="/study">
          今日の5問を始める
        </Link>
      </section>
      <section className="metrics">
        <div className="metric">
          <strong>{summary?.accuracy ?? 0}%</strong>
          <span>累計正答率</span>
        </div>
        <div className="metric">
          <strong>{summary?.due_reviews ?? 0}</strong>
          <span>復習待ち</span>
        </div>
      </section>
      <section className="panel stack">
        <h2>今日の内訳</h2>
        <div className="pill-row">
          {plan.items.map((item) => (
            <span className="pill" key={item.id}>
              {item.display_order}. {item.item_type}
            </span>
          ))}
        </div>
      </section>
      <section className="panel stack">
        <h2>いま優先する分野</h2>
        <p className="lead">{nextWeak ? `${nextWeak.subject_name} / ${nextWeak.topic_name}` : "回答が増えると苦手分野を表示します。"}</p>
      </section>
    </AppShell>
  );
}
