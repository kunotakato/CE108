"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { getPastExamThemes } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { PastExamThemeList } from "@/lib/types";

export default function PastExamsPage() {
  const [data, setData] = useState<PastExamThemeList | null>(null);
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
      setData(await getPastExamThemes(token, 200));
    } catch (err) {
      setError(err instanceof Error ? err.message : "過去問テーマを読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const themes = data?.themes || [];
  const refs = data?.items || [];

  return (
    <AppShell title="年度別・分野別">
      <section className="hero stack">
        <p className="eyebrow">AI頻出分析の土台</p>
        <h1>過去問の出題位置から、解くべきテーマを見つける。</h1>
        <p className="lead">
          公式問題文は保存せず、年度・午前/午後・問番号・頻出テーマ・CE108類題だけを扱います。
        </p>
      </section>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}

      {!loading && !error && refs.length === 0 ? (
        <EmptyState message="まだ過去問テーマは登録されていません。年度・午前/午後・問番号・分野だけを追加すると、頻出テーマ順に並べられます。" />
      ) : null}

      {themes.length ? (
        <section className="panel stack">
          <h2>頻出テーマ候補</h2>
          {themes.slice(0, 8).map((theme) => (
            <div className="strategy-card" key={`${theme.topic_code}-${theme.derived_theme}`}>
              <strong>{theme.derived_theme}</strong>
              <span>{theme.subject_name} / {theme.topic_name}</span>
              <span>出題位置 {theme.count}件 / 最新 第{theme.latest_exam_round}回</span>
              {theme.linked_question_id ? (
                <Link className="link-button" href={`/study?mode=frequent`}>
                  CE108類題で確認
                </Link>
              ) : null}
            </div>
          ))}
        </section>
      ) : null}

      {refs.length ? (
        <section className="panel stack">
          <h2>年度・午前午後・問番号</h2>
          {refs.map((ref) => (
            <article className="strategy-card" key={ref.id}>
              <strong>{ref.exam_label}</strong>
              <span>{ref.subject_name} / {ref.topic_name}</span>
              <span>{ref.derived_theme}</span>
              <div className="pill-row">
                <span className="pill">公式本文なし</span>
                <span className="pill">{ref.linked_question_id ? "CE108類題あり" : "類題準備中"}</span>
              </div>
            </article>
          ))}
        </section>
      ) : null}

      <section className="panel stack">
        <h2>有料模試への使い方</h2>
        <p className="muted">
          10年分の出題位置を蓄積し、よく出るテーマからCE108オリジナル問題と模試を作るための準備画面です。
        </p>
        <Link className="secondary-button" href="/strategy">学習戦略を見る</Link>
      </section>
    </AppShell>
  );
}
