"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { AnswerReviewPanel } from "@/components/AnswerReviewPanel";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { getAnsweredQuestion, getHistory } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { AnswerResult, LearningHistory } from "@/lib/types";

export default function HistoryPage() {
  const [history, setHistory] = useState<LearningHistory | null>(null);
  const [details, setDetails] = useState<Record<number, AnswerResult>>({});
  const [loading, setLoading] = useState(true);
  const [detailLoadingId, setDetailLoadingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  async function load() {
    const token = getToken();
    if (!token) {
      setError("ログイン情報が見つかりません。ログインし直してください。");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      setHistory(await getHistory(token, 50));
    } catch (err) {
      setError(err instanceof Error ? err.message : "学習履歴を読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

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

  useEffect(() => {
    void load();
  }, []);

  return (
    <AppShell title="学習履歴">
      <section className="hero stack">
        <p className="eyebrow">History</p>
        <h1>解いた問題を見返す。</h1>
        <p className="lead">直近50件の回答から、解説・図解・誤答選択肢の理由を確認できます。</p>
        <Link className="secondary-button" href="/home">ホームへ戻る</Link>
      </section>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {detailError ? <ErrorState message={detailError} /> : null}
      {!loading && !error && history?.items.length === 0 ? <EmptyState message="まだ回答履歴がありません。今日の5問から始めましょう。" /> : null}
      <div className="stack">
        {history?.items.map((item) => (
          <div className="stack" key={item.id}>
            <section className="panel stack">
              <div className="pill-row">
                <span className={`pill ${item.is_correct ? "pill-success" : "pill-danger"}`}>{item.is_correct ? "正解" : "誤答"}</span>
                <span className="pill">{item.subject_name}</span>
                <span className="pill">{item.answer_mode}</span>
              </div>
              <h2>{item.topic_name}</h2>
              <p className="lead">{item.question_text}</p>
              <p className="muted">
                回答日時: {item.answered_at} / 自信度: {item.confidence_level} / {item.response_time_seconds}秒
              </p>
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
