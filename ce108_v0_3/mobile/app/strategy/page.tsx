"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { ErrorState, LoadingState } from "@/components/StateViews";
import { addExamEvent, addScoreRecord, getStrategy, saveTargetExamDate } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { RadarSubject, ScoreRecordPayload, StudyMode, StudyStrategy } from "@/lib/types";

const subjectNames = [
  "医学概論・基礎医学",
  "臨床医学総論",
  "医用電気電子工学",
  "医用機械工学・物理数学",
  "生体機能代行装置学",
  "生体計測装置学",
  "医用機器安全管理学"
];

function RadarChart({ rows }: { rows: RadarSubject[] }) {
  const data = rows.slice(0, 7);
  const points = useMemo(() => {
    const center = 120;
    const radius = 92;
    return data.map((row, index) => {
      const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(1, data.length);
      const valueRadius = radius * Math.min(100, Math.max(0, row.value)) / 100;
      return {
        label: row.subject_name.replace("医用", "").replace("医学総論", "臨床"),
        x: center + Math.cos(angle) * valueRadius,
        y: center + Math.sin(angle) * valueRadius,
        lx: center + Math.cos(angle) * (radius + 18),
        ly: center + Math.sin(angle) * (radius + 18)
      };
    });
  }, [data]);
  const polygon = points.map((point) => `${point.x},${point.y}`).join(" ");
  return (
    <svg className="radar-chart" role="img" viewBox="0 0 240 240" aria-label="科目別レーダーチャート">
      {[0.25, 0.5, 0.75, 1].map((scale) => (
        <circle cx="120" cy="120" fill="none" key={scale} r={92 * scale} stroke="var(--line)" />
      ))}
      {points.map((point) => (
        <line key={`${point.label}-axis`} x1="120" x2={point.lx} y1="120" y2={point.ly} stroke="var(--line)" />
      ))}
      <polygon fill="rgba(22,67,59,.22)" points={polygon} stroke="var(--primary)" strokeWidth="2" />
      {points.map((point) => (
        <text className="radar-label" key={point.label} textAnchor="middle" x={point.lx} y={point.ly}>
          {point.label.slice(0, 4)}
        </text>
      ))}
    </svg>
  );
}

export default function StrategyPage() {
  const [strategy, setStrategy] = useState<StudyStrategy | null>(null);
  const [targetDate, setTargetDate] = useState("");
  const [eventTitle, setEventTitle] = useState("次回模試");
  const [eventDate, setEventDate] = useState("");
  const [scoreTitle, setScoreTitle] = useState("模試");
  const [totalScore, setTotalScore] = useState("");
  const [maxScore, setMaxScore] = useState("180");
  const [subjectScores, setSubjectScores] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
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
      const next = await getStrategy(token);
      setStrategy(next);
      setTargetDate(next.target_exam_date || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "戦略データを読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submitTarget(event: FormEvent) {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    setSaving(true);
    setError("");
    try {
      setStrategy(await saveTargetExamDate(token, targetDate));
    } catch (err) {
      setError(err instanceof Error ? err.message : "試験日を保存できませんでした。");
    } finally {
      setSaving(false);
    }
  }

  async function submitEvent(event: FormEvent) {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    setSaving(true);
    setError("");
    try {
      await addExamEvent(token, { event_type: "mock", title: eventTitle, event_date: eventDate });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "模試予定を保存できませんでした。");
    } finally {
      setSaving(false);
    }
  }

  async function submitScore(event: FormEvent) {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    const scores = Object.fromEntries(Object.entries(subjectScores).filter(([, value]) => value.trim()).map(([key, value]) => [key, Number(value)]));
    const payload: ScoreRecordPayload = {
      score_type: "mock",
      title: scoreTitle,
      taken_at: new Date().toISOString().slice(0, 10),
      total_score: Number(totalScore),
      max_score: Number(maxScore),
      subject_scores: scores
    };
    setSaving(true);
    setError("");
    try {
      await addScoreRecord(token, payload);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "点数を保存できませんでした。");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <AppShell title="戦略"><LoadingState /></AppShell>;

  const mode = (strategy?.recommended_mode || "balanced") as StudyMode;
  const modeLabels: Record<StudyMode, string> = { medical: "医学重点", engineering: "工学重点", balanced: "バランス" };

  return (
    <AppShell title="戦略">
      <section className="hero stack">
        <p className="eyebrow">{strategy?.phase_label || "学習戦略"}</p>
        <h1>{modeLabels[mode]}で進めましょう。</h1>
        <p className="lead">{strategy?.days_until_exam == null ? "試験日を入れると直前期の作戦まで切り替えます。" : `試験まで ${strategy.days_until_exam} 日。${strategy.recommendation}`}</p>
        <Link className="primary-button" href={`/study?mode=${mode}`}>{modeLabels[mode]}5問を解く</Link>
      </section>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <section className="panel stack">
        <h2>科目別レーダー</h2>
        <RadarChart rows={strategy?.radar || []} />
        <div className="pill-row">
          {(strategy?.weak_subjects || []).map((row) => <span className="pill" key={row.subject_code}>{row.subject_name}: {row.value}%</span>)}
        </div>
      </section>
      <section className="panel stack">
        <h2>モード選択</h2>
        <div className="mode-grid">
          <Link className="secondary-button" href="/study?mode=medical">医学重点</Link>
          <Link className="secondary-button" href="/study?mode=engineering">工学重点</Link>
          <Link className="secondary-button" href="/study?mode=balanced">バランス</Link>
        </div>
      </section>
      <form className="panel form" onSubmit={submitTarget}>
        <h2>試験日</h2>
        <label className="field">
          <span>自分の試験日</span>
          <input type="date" value={targetDate} onChange={(event) => setTargetDate(event.target.value)} />
        </label>
        <button className="primary-button" disabled={saving || !targetDate} type="submit">保存</button>
      </form>
      <form className="panel form" onSubmit={submitEvent}>
        <h2>模試予定</h2>
        <label className="field">
          <span>予定名</span>
          <input value={eventTitle} onChange={(event) => setEventTitle(event.target.value)} />
        </label>
        <label className="field">
          <span>予定日</span>
          <input type="date" value={eventDate} onChange={(event) => setEventDate(event.target.value)} />
        </label>
        <button className="primary-button" disabled={saving || !eventTitle || !eventDate} type="submit">模試予定を追加</button>
      </form>
      <form className="panel form" onSubmit={submitScore}>
        <h2>模試・過去問の点数</h2>
        <label className="field"><span>名称</span><input value={scoreTitle} onChange={(event) => setScoreTitle(event.target.value)} /></label>
        <div className="metrics">
          <label className="field"><span>総合点</span><input inputMode="decimal" value={totalScore} onChange={(event) => setTotalScore(event.target.value)} /></label>
          <label className="field"><span>満点</span><input inputMode="decimal" value={maxScore} onChange={(event) => setMaxScore(event.target.value)} /></label>
        </div>
        {subjectNames.map((name) => (
          <label className="field" key={name}>
            <span>{name} 正答率%</span>
            <input inputMode="decimal" value={subjectScores[name] || ""} onChange={(event) => setSubjectScores((current) => ({ ...current, [name]: event.target.value }))} />
          </label>
        ))}
        <button className="primary-button" disabled={saving || !scoreTitle || !totalScore || !maxScore} type="submit">点数を保存</button>
      </form>
      <section className="panel stack">
        <h2>予定</h2>
        {(strategy?.events || []).length ? strategy?.events.map((event) => (
          <p className="muted" key={event.id}>{event.event_date} / {event.title}</p>
        )) : <p className="muted">模試予定を入れるとここに表示します。</p>}
      </section>
    </AppShell>
  );
}
