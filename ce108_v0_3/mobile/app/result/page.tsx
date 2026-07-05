"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { getSession } from "@/lib/studySession";
import type { SessionAnswer } from "@/lib/types";

export default function ResultPage() {
  const [answers, setAnswers] = useState<SessionAnswer[]>([]);
  const [minutes, setMinutes] = useState(0);

  useEffect(() => {
    const session = getSession();
    setAnswers(session.answers);
    setMinutes(Math.max(1, Math.round((Date.now() - session.startedAt) / 60000)));
  }, []);

  const correct = answers.filter((answer) => answer.isCorrect).length;
  const accuracy = answers.length ? Math.round((correct / answers.length) * 100) : 0;
  const improved = answers.find((answer) => answer.isCorrect)?.topicName || "今日の範囲";

  return (
    <AppShell title="完了">
      <section className="hero stack">
        <p className="eyebrow">今日の5問</p>
        <h1>{answers.length ? "完了しました。" : "結果はまだありません。"}</h1>
        <p className="lead">{answers.length ? `${minutes}分で ${answers.length} 問回答しました。` : "今日の5問を回答すると結果が表示されます。"}</p>
      </section>
      <section className="metrics">
        <div className="metric">
          <strong>{correct}/{answers.length}</strong>
          <span>正解数</span>
        </div>
        <div className="metric">
          <strong>{accuracy}%</strong>
          <span>正答率</span>
        </div>
      </section>
      <section className="panel stack">
        <h2>今日伸びた分野</h2>
        <p className="lead">{improved}</p>
      </section>
      <section className="panel stack">
        <h2>次の復習</h2>
        {answers.length ? (
          answers.map((answer) => (
            <p className="muted" key={answer.questionId}>
              {answer.topicName || "問題"}: {answer.reviewDate}
            </p>
          ))
        ) : (
          <p className="muted">回答後に復習日を表示します。</p>
        )}
      </section>
      <Link className="primary-button" href="/home">ホームへ戻る</Link>
    </AppShell>
  );
}
