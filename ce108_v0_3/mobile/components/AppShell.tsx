import Link from "next/link";
import type { ReactNode } from "react";

type Props = {
  title?: string;
  children: ReactNode;
  nav?: boolean;
};

export function AppShell({ title = "CE108", children, nav = true }: Props) {
  return (
    <main className="app-shell">
      <header className="top-bar">
        <Link className="brand" href="/home" aria-label="CE108 home">
          CE108
        </Link>
        {title ? <span className="top-title">{title}</span> : null}
      </header>
      <div className="screen">{children}</div>
      {nav ? (
        <nav className="bottom-nav" aria-label="主要メニュー">
          <Link href="/home">ホーム</Link>
          <Link href="/study">今日の5問</Link>
          <Link href="/mastery">理解度</Link>
        </nav>
      ) : null}
    </main>
  );
}
