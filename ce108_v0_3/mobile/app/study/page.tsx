"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { BottomAction } from "@/components/BottomAction";
import { ChoiceCard } from "@/components/ChoiceCard";
import { ConfidenceSelector } from "@/components/ConfidenceSelector";
import { ProgressHeader } from "@/components/ProgressHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/StateViews";
import { VisualAidCard } from "@/components/VisualAid";
import { getFocusPlan, getQuestion, getToday, setBookmark, submitAnswer } from "@/lib/api";
import { getToken } from "@/lib/auth";
import { addSessionAnswer, ensureSession, getSession } from "@/lib/studySession";
import type { AnswerResult, DailyPlan, DailyPlanItem, Question, StudyMode } from "@/lib/types";

function buildSessionKey(plan: DailyPlan, mode: StudyMode | "daily") {
  return `${mode}:${plan.plan_date}:${plan.id}:${plan.items.slice(0, 5).map((item) => item.question_id).join("-")}`;
}

function StudyPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const mode = (searchParams.get("mode") || "daily") as StudyMode | "daily";
  const modeLabels: Record<StudyMode | "daily", string> = {
    daily: "今日の5問",
    medical: "医学重点",
    engineering: "工学重点",
    balanced: "バランス",
    wrong: "誤答だけ",
    frequent: "頻出テーマ",
    bookmarked: "ブックマーク"
  };
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
  const answerResultRef = useRef<HTMLDivElement | null>(null);

  const items = useMemo(() => plan?.items.slice(0, 5) ?? [], [plan]);
  const sessionKey = useMemo(() => (plan ? buildSessionKey(plan, mode) : "unloaded"), [mode, plan]);
  const answeredIds = new Set((sessionKey === "unloaded" ? [] : getSession(sessionKey).answers).map((answer) => answer.questionId));
  const item: DailyPlanItem | undefined = items[currentIndex];
  const currentQuestionId = item?.question_id;
  const allCompleted = items.length > 0 && items.every((planItem) => planItem.completed || answeredIds.has(planItem.question_id));

  const loadPlan = useCallback(async function loadPlan() {
    const token = getToken();
    if (!token) {
      setError("ログイン情報が見つかりません。ログインし直してください。");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const today = mode === "daily" ? await getToday(token) : await getFocusPlan(token, mode, 5);
      const nextItems = today.items.slice(0, 5);
      const nextIndex = nextItems.findIndex((planItem) => !planItem.completed);
      ensureSession(buildSessionKey(today, mode));
      setPlan(today);
      setCurrentIndex(nextIndex >= 0 ? nextIndex : nextItems.length);
      setQuestion(null);
      setResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "今日の問題を読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }, [mode]);

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
  }, [loadPlan]);

  useEffect(() => {
    if (currentQuestionId) {
      void loadQuestion(currentQuestionId);
    } else {
      setQuestion(null);
    }
  }, [currentQuestionId]);

  useEffect(() => {
    if (result && answerResultRef.current) {
      answerResultRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

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
        answer_mode: mode === "daily" ? "daily" : mode
      });
      setResult(answer);
      addSessionAnswer(sessionKey, {
        questionId: question.id,
        subjectName: question.subject_name,
        topicName: question.topic_name,
        isCorrect: answer.is_correct,
        reviewDate: answer.review_date || "",
        seconds
      });
      setPlan((current) => current ? {
        ...current,
        items: current.items.map((planItem) => planItem.question_id === question.id ? { ...planItem, completed: 1 } : planItem)
      } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "回答を保存できませんでした。");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleBookmark(bookmarked: boolean) {
    if (!result?.question) return;
    const token = getToken();
    if (!token) return;
    setError("");
    try {
      await setBookmark(token, result.question.id, bookmarked);
      setResult((current) => current ? {
        ...current,
        question: { ...current.question, is_bookmarked: bookmarked }
      } : current);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ブックマークを更新できませんでした。");
    }
  }

  function next() {
    const latestAnsweredIds = new Set(getSession(sessionKey).answers.map((answer) => answer.questionId));
    const nextIndex = items.findIndex((planItem, index) => index > currentIndex && !planItem.completed && !latestAnsweredIds.has(planItem.question_id));
    if (nextIndex >= 0) {
      setCurrentIndex(nextIndex);
      return;
    }
    const remainingIndex = items.findIndex((planItem) => !planItem.completed && !latestAnsweredIds.has(planItem.question_id));
    if (remainingIndex >= 0) {
      setCurrentIndex(remainingIndex);
      return;
    }
    router.push("/result");
  }

  const numericValue = Number(numeric);
  const canSubmit = question?.question_type === "numeric" ? numeric.trim() !== "" && Number.isFinite(numericValue) : selected.length > 0;

  if (loading && !question) {
    return (
      <AppShell title={modeLabels[mode] || "重点5問"} nav={false} bottomAction>
        <LoadingState />
      </AppShell>
    );
  }

  if (error && !question) {
    return (
      <AppShell title={modeLabels[mode] || "重点5問"} nav={false} bottomAction>
        <ErrorState message={error} onRetry={item ? () => loadQuestion(item.question_id) : loadPlan} />
        <Link className="link-button" href="/home">ホームへ戻る</Link>
      </AppShell>
    );
  }

  if (allCompleted && !result) {
    return (
      <AppShell title={modeLabels[mode] || "重点5問"} nav={false} bottomAction>
        <EmptyState message="今日の5問は完了しています。" />
        <BottomAction onClick={() => router.push("/result")}>結果を見る</BottomAction>
      </AppShell>
    );
  }

  if (!item || !question) {
    return (
      <AppShell title={modeLabels[mode] || "重点5問"} nav={false} bottomAction>
        <EmptyState message="今日の問題がありません。" />
        <BottomAction onClick={() => router.push("/home")}>ホームへ戻る</BottomAction>
      </AppShell>
    );
  }

  return (
    <AppShell title={plan?.mode_label || "今日の5問"} nav={false} bottomAction>
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
          <section className="panel stack answer-result" ref={answerResultRef}>
            <div className="result-heading">
              <span className="pill">解説と図解</span>
              <span className="pill">{result.question.answer_statistics?.label || "回答を保存しました"}</span>
            </div>
            <h2 className={result.is_correct ? "correct" : "incorrect"}>{result.is_correct ? "正解です" : "復習しましょう"}</h2>
            <button
              className="secondary-button"
              type="button"
              onClick={() => handleBookmark(!result.question.is_bookmarked)}
            >
              {result.question.is_bookmarked ? "ブックマーク解除" : "ブックマークする"}
            </button>
            {result.question.learning_point ? (
              <div className="pill-row">
                <span className="pill">学習ポイント</span>
              </div>
            ) : null}
            {result.question.learning_point ? <p className="lead-small">{result.question.learning_point}</p> : null}
            <VisualAidCard aid={result.question.visual_aid} />
            <div className="explanation">
              <p>{result.question.explanation_standard || result.question.explanation_short || "解説は登録されていません。"}</p>
              <p className="muted">復習日: {result.review_date}</p>
            </div>
            {result.question.choice_feedback?.length ? (
              <div className="choice-feedback-list">
                {result.question.choice_feedback.map((choice) => (
                  <article
                    className={`choice-feedback ${choice.is_correct ? "correct-choice" : choice.selected ? "selected-wrong-choice" : ""}`}
                    key={choice.choice_code}
                  >
                    <div className="choice-feedback-header">
                      <span className="choice-code">{choice.choice_code}</span>
                      <span>{choice.feedback_label}</span>
                    </div>
                    <p className="choice-feedback-text">{choice.choice_text}</p>
                    <p className="muted">{choice.explanation || "この選択肢の解説は登録されていません。"}</p>
                  </article>
                ))}
              </div>
            ) : null}
            {result.related_questions?.length ? (
              <div className="related-question-list">
                <h3>この知識を太くする問題</h3>
                {result.related_questions.map((related) => (
                  <button
                    className="related-question"
                    key={related.id}
                    type="button"
                    onClick={() => {
                      const relatedIndex = items.findIndex((planItem) => planItem.question_id === related.id);
                      if (relatedIndex >= 0) {
                        setCurrentIndex(relatedIndex);
                        void loadQuestion(related.id);
                      }
                    }}
                    disabled={items.every((planItem) => planItem.question_id !== related.id)}
                  >
                    <span>{related.topic_name}</span>
                    <strong>{related.question_text}</strong>
                  </button>
                ))}
              </div>
            ) : null}
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

export default function StudyPage() {
  return (
    <Suspense fallback={<AppShell title="今日の5問" nav={false} bottomAction><LoadingState /></AppShell>}>
      <StudyPageContent />
    </Suspense>
  );
}
