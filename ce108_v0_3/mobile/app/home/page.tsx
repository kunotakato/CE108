"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { getDailyStatus, getMastery, getStrategy, getSummary, getToday } from "@/lib/api";
import { getStoredUser, getToken } from "@/lib/auth";
import type { DailyPlan, DailyStatus, LearningSummary, MasteryRow, StudyStrategy, User } from "@/lib/types";

export default function HomePage() {
  const [user, setUser] = useState<User | null>(null);
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [dailyStatus, setDailyStatus] = useState<DailyStatus | null>(null);
  const [summary, setSummary] = useState<LearningSummary | null>(null);
  const [mastery, setMastery] = useState<MasteryRow[]>([]);
  const [strategy, setStrategy] = useState<StudyStrategy | null>(null);
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
      const [today, status, learning, weak, nextStrategy] = await Promise.all([getToday(token), getDailyStatus(token), getSummary(token), getMastery(token, 3), getStrategy(token)]);
      setPlan(today);
      setDailyStatus(status);
      setSummary(learning);
      setMastery(weak);
      setStrategy(nextStrategy);
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
        <div className="metric">
          <strong>{summary?.weekly_answers ?? 0}</strong>
          <span>7日回答</span>
        </div>
        <div className="metric">
          <strong>{summary?.question_bank_total ?? 0}</strong>
          <span>公開問題</span>
        </div>
      </section>
      <section className="panel stack">
        <h2>今日の作戦</h2>
        <p className="lead">{strategy?.readiness_label || "現在地を集計中です。"}</p>
        <div className="strategy-card-list">
          {(strategy?.next_actions || []).slice(0, 3).map((action) => (
            <Link className="strategy-card" href={`/study?mode=${action.mode}`} key={`${action.mode}-${action.label}`}>
              <strong>{action.label}</strong>
              <span>{action.reason}</span>
            </Link>
          ))}
        </div>
        {strategy?.latest_score_rate != null ? (
          <p className="muted">直近スコア {strategy.latest_score_rate}% / 目標 {strategy.target_score_rate}%</p>
        ) : (
          <p className="muted">模試や過去問の点数を入れると、今日の作戦が具体化します。</p>
        )}
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
        <p className="muted">今週 {summary?.weekly_answers ?? 0} 問 / 正答率 {summary?.weekly_accuracy ?? 0}%</p>
      </section>
      <section className="panel stack">
        <h2>問題バンク</h2>
        <div className="mastery-bar" aria-label={`問題バンク ${summary?.bank_progress ?? 0}%`}>
          <div style={{ width: `${Math.min(100, Math.max(0, summary?.bank_progress ?? 0))}%` }} />
        </div>
        <p className="muted">{summary?.question_bank_total ?? 0}/{summary?.bank_goal ?? 300}問。毎日違う問題に触れられる土台を増やしています。</p>
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
        <Link className="secondary-button" href="/history">学習履歴を見る</Link>
      </section>
      <section className="panel stack">
        <h2>目的別に解く</h2>
        <div className="mode-grid">
          <Link className="secondary-button" href="/study?mode=wrong">間違えた問題だけ</Link>
          <Link className="secondary-button" href="/study?mode=frequent">頻出テーマ</Link>
          <Link className="secondary-button" href="/study?mode=bookmarked">ブックマーク</Link>
          <Link className="secondary-button" href="/study?mode=first_paid">有料候補30問</Link>
        </div>
        <p className="muted">通常期は苦手を潰し、直前期は頻出・得意分野を伸ばす使い方を想定しています。</p>
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
