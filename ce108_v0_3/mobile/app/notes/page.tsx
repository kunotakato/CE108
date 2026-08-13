"use client";

import { useMemo, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ConfidenceSelector } from "@/components/ConfidenceSelector";
import { EmptyState, ErrorState } from "@/components/StateViews";
import { answerNoteQuestion, createNote, generateNoteQuestions } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { NoteQuestion } from "@/lib/types";

export default function NotesPage() {
  const startedAt = useRef(Date.now());
  const [title, setTitle] = useState("今日の授業ノート");
  const [content, setContent] = useState("");
  const [count, setCount] = useState(5);
  const [questions, setQuestions] = useState<NoteQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selected, setSelected] = useState("");
  const [confidence, setConfidence] = useState("たぶん分かる");
  const [answered, setAnswered] = useState<NoteQuestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const current = questions[currentIndex];
  const canGenerate = content.trim().length >= 20 && !loading;
  const answeredCount = useMemo(() => questions.filter((question) => question.answered).length, [questions]);

  async function handleFileChange(file: File | null) {
    if (!file) return;
    setError("");
    const lowerName = file.name.toLowerCase();
    const isTextFile =
      file.type.startsWith("text/") ||
      lowerName.endsWith(".txt") ||
      lowerName.endsWith(".md") ||
      lowerName.endsWith(".csv");
    if (!isTextFile) {
      setError("写真・PDFの読み取りは次の段階で対応予定です。今は.txt、.md、.csvの学習メモを読み込めます。");
      return;
    }
    if (file.size > 20000) {
      setError("v0.4.3では20KB以内のテキストファイルを読み込めます。長いノートは必要な部分だけにしてください。");
      return;
    }
    try {
      const text = await file.text();
      setTitle(file.name.replace(/\.[^.]+$/, "") || "読み込みノート");
      setContent(text);
    } catch {
      setError("ファイルを読み込めませんでした。文字コードをUTF-8にして再度試してください。");
    }
  }

  async function handleGenerate() {
    const token = getToken();
    if (!token) {
      setError("ログイン情報が見つかりません。ログインし直してください。");
      return;
    }
    setLoading(true);
    setError("");
    setQuestions([]);
    setCurrentIndex(0);
    setAnswered(null);
    setSelected("");
    try {
      const note = await createNote(token, { title, content, source_type: "manual_note" });
      const generated = await generateNoteQuestions(token, note.note_id, count);
      setQuestions(generated.questions);
      startedAt.current = Date.now();
    } catch (err) {
      setError(err instanceof Error ? err.message : "ノートから問題を作成できませんでした。");
    } finally {
      setLoading(false);
    }
  }

  async function handleAnswer() {
    const token = getToken();
    if (!token || !current || !selected) return;
    const seconds = Math.max(1, Math.round((Date.now() - startedAt.current) / 1000));
    setLoading(true);
    setError("");
    try {
      const result = await answerNoteQuestion(token, current.id, {
        selected_code: selected,
        confidence,
        response_time_seconds: seconds
      });
      setAnswered(result.question);
      setQuestions((items) => items.map((item) => (item.id === current.id ? { ...item, answered: true } : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "回答を保存できませんでした。");
    } finally {
      setLoading(false);
    }
  }

  function nextQuestion() {
    const next = Math.min(currentIndex + 1, questions.length - 1);
    setCurrentIndex(next);
    setSelected("");
    setAnswered(null);
    startedAt.current = Date.now();
  }

  return (
    <AppShell title="ノートAI">
      <div className="stack">
        <section className="hero stack">
          <p className="eyebrow">Notebook to quiz</p>
          <h1>自分のノートから、復習問題を作る。</h1>
          <p className="lead">CE108が重要そうな文を拾い、国家試験対策用のオリジナル問題に変換します。</p>
          <p className="muted">外部βでは個人情報、患者情報、学校の非公開資料、支払い情報を入力しないでください。</p>
        </section>
        <section className="panel stack">
          <label className="field">
            <span>ノート名</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} />
          </label>
          <label className="field">
            <span>ノート本文</span>
            <textarea
              className="note-textarea"
              value={content}
              onChange={(event) => setContent(event.target.value)}
              placeholder="授業メモ、実習メモ、模試の復習メモを貼り付けてください。"
            />
          </label>
          <label className="field">
            <span>ファイルから読み込む</span>
            <input accept=".txt,.md,.csv,text/plain,text/markdown,text/csv,image/*,application/pdf" type="file" onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)} />
          </label>
          <label className="field">
            <span>作成する問題数</span>
            <input
              inputMode="numeric"
              max={10}
              min={1}
              type="number"
              value={count}
              onChange={(event) => setCount(Math.max(1, Math.min(10, Number(event.target.value) || 1)))}
            />
          </label>
          <button className="primary-button" disabled={!canGenerate} type="button" onClick={handleGenerate}>
            {loading ? "作成中" : "ノートから問題を作る"}
          </button>
          <p className="muted">v0.4.3では外部AI APIを使わず、ローカルの重要文抽出で生成します。公式過去問ではなく復習用オリジナル問題です。生成内容は誤る可能性があるため、解説とノートを照合してください。写真・PDFのOCRは次の段階で対応予定です。</p>
        </section>
        {error ? <ErrorState message={error} /> : null}
        {questions.length ? (
          <section className="panel stack">
            <div className="pill-row">
              <span className="pill">{currentIndex + 1}/{questions.length}</span>
              <span className="pill">回答済み {answeredCount}</span>
              <span className="pill">{current?.topic_code}</span>
            </div>
            <h2>{current.question_text}</h2>
            <div className="choice-list">
              {current.choices.map((choice) => (
                <button
                  className={`choice-card ${selected === choice.choice_code ? "selected" : ""}`}
                  disabled={Boolean(answered)}
                  key={choice.choice_code}
                  type="button"
                  onClick={() => setSelected(choice.choice_code)}
                >
                  <span className="choice-code">{choice.choice_code}</span>
                  <span>{choice.choice_text}</span>
                </button>
              ))}
            </div>
            <ConfidenceSelector value={confidence} onChange={setConfidence} />
            {answered ? (
              <div className="stack">
                <h3 className={answered.choice_feedback?.some((choice) => choice.selected && choice.is_correct) ? "correct" : "incorrect"}>
                  {answered.choice_feedback?.some((choice) => choice.selected && choice.is_correct) ? "正解です" : "復習しましょう"}
                </h3>
                <p className="explanation">{answered.explanation}</p>
                <div className="choice-feedback-list">
                  {answered.choice_feedback?.map((choice) => (
                    <article className={`choice-feedback ${choice.is_correct ? "correct-choice" : choice.selected ? "selected-wrong-choice" : ""}`} key={choice.choice_code}>
                      <div className="choice-feedback-header">
                        <span className="choice-code">{choice.choice_code}</span>
                        <span>{choice.is_correct ? "正答" : choice.selected ? "選んだ誤答" : "誤答"}</span>
                      </div>
                      <p className="choice-feedback-text">{choice.choice_text}</p>
                      <p className="muted">{choice.explanation}</p>
                    </article>
                  ))}
                </div>
                <button className="secondary-button" disabled={currentIndex + 1 >= questions.length} type="button" onClick={nextQuestion}>
                  次のノート問題へ
                </button>
              </div>
            ) : (
              <button className="primary-button" disabled={!selected || loading} type="button" onClick={handleAnswer}>
                回答する
              </button>
            )}
          </section>
        ) : (
          <EmptyState message="ノートを入力すると、ここにAI生成問題が表示されます。" />
        )}
      </div>
    </AppShell>
  );
}
