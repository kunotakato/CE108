"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorState } from "@/components/StateViews";
import { submitFeedback } from "@/lib/api";
import { getToken } from "@/lib/auth";

const categories = ["使いやすさ", "問題・解説", "不具合", "要望", "その他"];

export default function FeedbackPage() {
  const [rating, setRating] = useState(4);
  const [category, setCategory] = useState(categories[0]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const token = getToken();
    if (!token) {
      setError("ログイン情報が見つかりません。ログインし直してください。");
      return;
    }
    setLoading(true);
    setError("");
    setSaved(false);
    try {
      await submitFeedback(token, {
        rating,
        category,
        message,
        page_url: window.location.href,
        user_agent: window.navigator.userAgent
      });
      setSaved(true);
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "フィードバックを送信できませんでした。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell title="フィードバック">
      <section className="hero stack">
        <p className="eyebrow">Beta Feedback</p>
        <h1>使ってみた感想を送る</h1>
        <p className="lead">外部β検証の改善に使います。個別返信が必要な内容は、別途連絡先を添えて管理者へ共有してください。</p>
      </section>
      <form className="panel form" onSubmit={handleSubmit}>
        <label className="field">
          <span>評価</span>
          <select value={rating} onChange={(event) => setRating(Number(event.target.value))}>
            <option value={5}>5 とても使いやすい</option>
            <option value={4}>4 使いやすい</option>
            <option value={3}>3 普通</option>
            <option value={2}>2 使いにくい</option>
            <option value={1}>1 続けにくい</option>
          </select>
        </label>
        <label className="field">
          <span>種別</span>
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>内容</span>
          <textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="例: 解説は分かりやすいが、次に何をすればよいかをもっと目立たせたい。" />
        </label>
        <button className="primary-button" disabled={loading || message.trim().length < 3} type="submit">
          {loading ? "送信中" : "送信する"}
        </button>
      </form>
      {saved ? (
        <section className="panel stack">
          <h2>送信しました</h2>
          <p className="muted">ありがとうございます。β版の改善に反映します。</p>
          <Link className="secondary-button" href="/home">ホームへ戻る</Link>
        </section>
      ) : null}
      {error ? <ErrorState message={error} /> : null}
    </AppShell>
  );
}
