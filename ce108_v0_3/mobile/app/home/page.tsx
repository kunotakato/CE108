"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { getDailyStatus, getMastery, getSummary, getToday } from "@/lib/api";
import { getStoredUser, getToken } from "@/lib/auth";
import type { DailyPlan, DailyStatus, LearningSummary, MasteryRow, User } from "@/lib/types";

export default function HomePage() {
  const [user, setUser] = useState<User | null>(null);
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [dailyStatus, setDailyStatus] = useState<DailyStatus | null>(null);
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
      const [today, status, learning, weak] = await Promise.all([getToday(token), getDailyStatus(token), getSummary(token), getMastery(token, 3)]);
      setPlan(today);
      setDailyStatus(status);
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
  const actionLabel = dailyStatus?.next_action || "今日の5問を始める";
  const actionHref = dailyStatus?.due_reviews ? "/reviews" : "/study";

  return (
    <AppShell title="ホーム">
      <section className="hero stack">
        <p className="eyebrow">{user?.display_name || "学生"}さんの今日</p>
        <h1>{dailyStatus?.status === "completed" ? "今日は完了です。" : "今日も少しだけ進めましょう。"}</h1>
        <p className="lead">{plan.estimated_minutes}分目安。完了済み {dailyStatus?.completed_count ?? completed}/{dailyStatus?.total_count ?? plan.items.length} 問。</p>
        <Link className="primary-button" href={actionHref}>
          {actionLabel}
        </Link>
      </section>
      <section className="metrics">
        <div className="metric">
          <strong>{dailyStatus?.streak_days ?? 0}日</strong>
          <span>連続学習</span>
        </div>
        <div className="metric">
          <strong>{summary?.due_reviews ?? 0}</strong>
          <span>復習待ち</span>
        </div>
      </section>
      <section className="panel stack">
        <h2>7日間の学習</h2>
        <div className="week-row" aria-label="週間学習状況">
          {(dailyStatus?.weekly ?? []).map((day) => (
            <span className={`day-dot ${day.completed ? "done" : ""}`} key={day.date}>
              {new Date(`${day.date}T00:00:00`).getDate()}
            </span>
          ))}
        </div>
        <p className="muted">{dailyStatus?.tomorrow_preview.message}</p>
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
        <Link className="secondary-button" href="/mastery">理解度を見る</Link>
      </section>
      <section className="panel stack">
        <h2>ノートから問題作成</h2>
        <p className="muted">授業メモや模試復習メモから、CE108が重要点を拾ってオリジナル問題を作ります。</p>
        <Link className="secondary-button" href="/notes">ノートAIを使う</Link>
      </section>
      <section className="panel stack">
        <h2>β版への感想</h2>
        <p className="muted">外部β検証では、使いやすさ・分かりにくさ・不具合を集めています。</p>
        <Link className="secondary-button" href="/feedback">フィードバックを送る</Link>
      </section>
    </AppShell>
  );
}
