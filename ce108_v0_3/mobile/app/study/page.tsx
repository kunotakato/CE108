"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { BottomAction } from "@/components/BottomAction";
import { ChoiceCard } from "@/components/ChoiceCard";
import { ConfidenceSelector } from "@/components/ConfidenceSelector";
import { ProgressHeader } from "@/components/ProgressHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { getQuestion, getToday, submitAnswer } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { addSessionAnswer, getSession, resetSession } from "@/lib/studySession";
import type { AnswerResult, DailyPlan, DailyPlanItem, Question } from "@/lib/types";

export default function StudyPage() {
  const router = useRouter();
  const startedAt = useRef(Date.now());
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [question, setQuestion] = useState<Question | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [numeric, setNumeric] = useState("");
  const [confidence, setConfidence] = useState("たぶん分かる");
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const items = useMemo(() => plan?.items.slice(0, 5) ?? [], [plan]);
  const item: DailyPlanItem | undefined = items[currentIndex];
  const currentQuestionId = item?.question_id;

  async function loadPlan() {
    const token = getToken();
    if (!token) {
      setError("ログイン情報が見つかりません。ログインし直してください。");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const today = await getToday(token);
      setPlan(today);
      if (getSession().answers.length === 0) resetSession();
    } catch (err) {
      setError(err instanceof Error ? err.message : "今日の問題を読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

  async function loadQuestion(questionId: number) {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError("");
    setResult(null);
    setSelected([]);
    setNumeric("");
    setConfidence("たぶん分かる");
    startedAt.current = Date.now();
    try {
      setQuestion(await getQuestion(token, questionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "問題を読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPlan();
  }, []);

  useEffect(() => {
    if (currentQuestionId) void loadQuestion(currentQuestionId);
  }, [currentQuestionId]);

  function toggleChoice(code: string) {
    if (!question || result) return;
    if (question.question_type === "multiple") {
      setSelected((current) => (current.includes(code) ? current.filter((itemCode) => itemCode !== code) : [...current, code]));
    } else {
      setSelected([code]);
    }
  }

  async function handleSubmit() {
    if (!question || submitting || result) return;
    const token = getToken();
    if (!token) return;
    const seconds = Math.max(1, Math.round((Date.now() - startedAt.current) / 1000));
    const numericValue = question.question_type === "numeric" ? Number(numeric) : null;
    if (question.question_type === "numeric" && (numeric.trim() === "" || !Number.isFinite(numericValue))) {
      setError("数値で回答してください。");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const answer = await submitAnswer(token, question.id, {
        selected_codes: question.question_type === "numeric" ? [] : selected,
        numeric_answer: numericValue,
        confidence,
        response_time_seconds: seconds,
        answer_mode: "daily"
      });
      setResult(answer);
      addSessionAnswer({
        questionId: question.id,
        subjectName: question.subject_name,
        topicName: question.topic_name,
        isCorrect: answer.is_correct,
        reviewDate: answer.review_date,
        seconds
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "回答を保存できませんでした。");
    } finally {
      setSubmitting(false);
    }
  }

  function next() {
    if (currentIndex + 1 >= items.length || getSession().answers.length >= 5) {
      router.push("/result");
      return;
    }
    setCurrentIndex((current) => current + 1);
  }

  const numericValue = Number(numeric);
  const canSubmit = question?.question_type === "numeric" ? numeric.trim() !== "" && Number.isFinite(numericValue) : selected.length > 0;

  if (loading && !question) {
    return (
      <AppShell title="今日の5問" nav={false}>
        <LoadingState />
      </AppShell>
    );
  }

  if (error && !question) {
    return (
      <AppShell title="今日の5問" nav={false}>
        <ErrorState message={error} onRetry={item ? () => loadQuestion(item.question_id) : loadPlan} />
        <Link className="link-button" href="/home">ホームへ戻る</Link>
      </AppShell>
    );
  }

  if (!item || !question) {
    return (
      <AppShell title="今日の5問" nav={false}>
        <EmptyState message="今日の問題がありません。" />
        <BottomAction onClick={() => router.push("/home")}>ホームへ戻る</BottomAction>
      </AppShell>
    );
  }

  return (
    <AppShell title="今日の5問" nav={false}>
      <div className="stack">
        <ProgressHeader current={currentIndex + 1} total={items.length} />
        <section className="question-card stack">
          <div className="pill-row">
            <span className="pill">{item.item_type}</span>
            <span className="pill">{question.subject_name}</span>
          </div>
          <p className="question-text">{question.question_text}</p>
          {question.question_type === "numeric" ? (
            <label className="field">
              <span>数値で回答{question.unit ? `（${question.unit}）` : ""}</span>
              <input
                className="numeric-input"
                inputMode="decimal"
                value={numeric}
                onChange={(event) => setNumeric(event.target.value)}
                placeholder="数値を入力"
              />
            </label>
          ) : (
            <div className="choice-list">
              {question.choices.map((choice) => (
                <ChoiceCard
                  code={choice.choice_code}
                  key={choice.choice_code}
                  selected={selected.includes(choice.choice_code)}
                  text={choice.choice_text}
                  onSelect={() => toggleChoice(choice.choice_code)}
                />
              ))}
            </div>
          )}
          <ConfidenceSelector value={confidence} onChange={setConfidence} />
        </section>
        {error ? <ErrorState message={error} /> : null}
        {result ? (
          <section className="panel stack">
            <h2 className={result.is_correct ? "correct" : "incorrect"}>{result.is_correct ? "正解です" : "復習しましょう"}</h2>
            <div className="explanation">
              <p>{result.question.explanation_standard || result.question.explanation_short || "解説は登録されていません。"}</p>
              <p className="muted">復習日: {result.review_date}</p>
            </div>
          </section>
        ) : null}
      </div>
      <BottomAction
        disabled={!canSubmit || submitting || Boolean(result)}
        secondary={
          result ? (
            <button className="secondary-button" type="button" onClick={next}>
              {currentIndex + 1 >= items.length ? "結果を見る" : "次の問題へ"}
            </button>
          ) : null
        }
        onClick={handleSubmit}
      >
        {submitting ? "保存中" : result ? "回答済み" : "回答する"}
      </BottomAction>
    </AppShell>
  );
}
