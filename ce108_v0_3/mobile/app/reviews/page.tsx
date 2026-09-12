"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { AnswerReviewPanel } from "@/components/AnswerReviewPanel";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { getAnsweredQuestion, getReviewQueue } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { AnswerResult, ReviewQueue } from "@/lib/types";

export default function ReviewsPage() {
  const [queue, setQueue] = useState<ReviewQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [details, setDetails] = useState<Record<number, AnswerResult>>({});
  const [detailError, setDetailError] = useState("");
  const [detailLoadingId, setDetailLoadingId] = useState<number | null>(null);

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

  async function showDetail(questionId: number) {
    const token = getToken();
    if (!token) {
      setDetailError("ログイン情報が見つかりません。");
      return;
    }
    if (details[questionId]) return;
    setDetailLoadingId(questionId);
    setDetailError("");
    try {
      const detail = await getAnsweredQuestion(token, questionId);
      setDetails((current) => ({ ...current, [questionId]: detail }));
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "解説を読み込めませんでした。");
    } finally {
      setDetailLoadingId(null);
    }
  }

  return (
    <AppShell title="復習">
      <section className="hero stack">
        <p className="eyebrow">Review Queue</p>
        <h1>今日の復習を片づけましょう。</h1>
        <p className="lead">今日までの復習 {queue?.due_count ?? 0} 件、今後の予定 {queue?.upcoming_count ?? 0} 件。</p>
        <Link className="primary-button" href="/study">今日の5問へ進む</Link>
        <div className="mode-grid">
          <Link className="secondary-button" href="/study?mode=wrong">間違えた問題だけ解く</Link>
          <Link className="secondary-button" href="/study?mode=bookmarked">ブックマークを解く</Link>
        </div>
      </section>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {detailError ? <ErrorState message={detailError} /> : null}
      {!loading && !error && queue?.items.length === 0 ? <EmptyState message="復習予定はありません。今日の5問から始めましょう。" /> : null}
      <div className="stack">
        {queue?.items.map((item) => (
          <div className="stack" key={item.review_id}>
            <section className="panel stack">
              <div className="pill-row">
                <span className="pill">{item.review_label}</span>
                <span className="pill">{item.subject_name}</span>
              </div>
              <h2>{item.topic_name}</h2>
              <p className="lead">{item.question_text}</p>
              <p className="muted">{item.reason} / 予定日: {item.scheduled_date}</p>
              <button className="secondary-button" type="button" onClick={() => showDetail(item.question_id)}>
                {detailLoadingId === item.question_id ? "読み込み中" : details[item.question_id] ? "解説を表示中" : "解説と図解を見る"}
              </button>
            </section>
            {details[item.question_id] ? <AnswerReviewPanel detail={details[item.question_id]} /> : null}
          </div>
        ))}
      </div>
    </AppShell>
  );
}
