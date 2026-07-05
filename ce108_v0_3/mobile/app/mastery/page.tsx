"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorState, LoadingState } from "@/components/StateViews";
import { getMastery } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { MasteryRow } from "@/lib/types";

export default function MasteryPage() {
  const [rows, setRows] = useState<MasteryRow[]>([]);
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
      setRows(await getMastery(token, 3));
    } catch (err) {
      setError(err instanceof Error ? err.message : "理解度を読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <AppShell title="理解度">
      <section className="hero stack">
        <p className="eyebrow">苦手・得意分析</p>
        <h1>優先して復習する3分野</h1>
        <p className="lead">低い理解度の分野から表示します。</p>
      </section>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <div className="stack">
        {rows.map((row) => (
          <section className="panel stack" key={`${row.subject_name}-${row.topic_name}`}>
            <h2>{row.topic_name}</h2>
            <p className="muted">{row.subject_name}</p>
            <div className="mastery-bar" aria-label={`理解度 ${row.mastery_score}%`}>
              <div style={{ width: `${Math.min(100, Math.max(0, row.mastery_score))}%` }} />
            </div>
            <p className="muted">
              理解度 {row.mastery_score}% / 回答 {row.total_answers} 件
            </p>
          </section>
        ))}
      </div>
      <Link className="primary-button" href="/study">今日の5問へ</Link>
    </AppShell>
  );
}
