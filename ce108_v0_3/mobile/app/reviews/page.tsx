"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { getReviewQueue } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ReviewQueue } from "@/lib/types";

export default function ReviewsPage() {
  const [queue, setQueue] = useState<ReviewQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    const token = getToken();
    if (!token) {
      setError("ログイン情報が見つかりません。");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setQueue(await getReviewQueue(token, 20));
    } catch (err) {
      setError(err instanceof Error ? err.message : "復習予定を読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <AppShell title="復習">
      <section className="hero stack">
        <p className="eyebrow">Review Queue</p>
        <h1>今日の復習を片づけましょう。</h1>
        <p className="lead">今日までの復習 {queue?.due_count ?? 0} 件、今後の予定 {queue?.upcoming_count ?? 0} 件。</p>
        <Link className="primary-button" href="/study">今日の5問へ進む</Link>
      </section>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error && queue?.items.length === 0 ? <EmptyState message="復習予定はありません。今日の5問から始めましょう。" /> : null}
      <div className="stack">
        {queue?.items.map((item) => (
          <section className="panel stack" key={item.review_id}>
            <div className="pill-row">
              <span className="pill">{item.review_label}</span>
              <span className="pill">{item.subject_name}</span>
            </div>
            <h2>{item.topic_name}</h2>
            <p className="lead">{item.question_text}</p>
            <p className="muted">{item.reason} / 予定日: {item.scheduled_date}</p>
          </section>
        ))}
      </div>
    </AppShell>
  );
}
