"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { BottomAction } from "@/components/BottomAction";
import { completeOnboarding } from "@/lib/auth";

export default function OnboardingPage() {
  const router = useRouter();
  const [minutes, setMinutes] = useState("15");
  const [weakArea, setWeakArea] = useState("基礎医学");
  const [time, setTime] = useState("21:00");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  function finish() {
    completeOnboarding({ minutes, weakArea, time });
    router.replace("/home");
  }

  return (
    <AppShell title="初期設定" nav={false} bottomAction>
      <section className="hero stack">
        <p className="eyebrow">はじめに</p>
        <h1>毎日続ける量を決めましょう。</h1>
        <p className="lead">ここでの設定はモバイル画面内だけで使います。v0.3.5 では外部通知とは接続していません。</p>
      </section>
      <section className="panel form">
        <label className="field">
          <span>1日の目安</span>
          <select value={minutes} onChange={(event) => setMinutes(event.target.value)}>
            <option value="10">10分</option>
            <option value="15">15分</option>
            <option value="20">20分</option>
          </select>
        </label>
        <label className="field">
          <span>気になる分野</span>
          <select value={weakArea} onChange={(event) => setWeakArea(event.target.value)}>
            <option>基礎医学</option>
            <option>臨床医学</option>
            <option>公衆衛生</option>
          </select>
        </label>
        <label className="field">
          <span>学習したい時間</span>
          <input type="time" value={time} onChange={(event) => setTime(event.target.value)} />
        </label>
      </section>
      <BottomAction disabled={!ready} onClick={finish}>ホームへ進む</BottomAction>
    </AppShell>
  );
}
