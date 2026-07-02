type Props = {
  current: number;
  total: number;
};

export function ProgressHeader({ current, total }: Props) {
  const percent = Math.min(100, Math.round((current / Math.max(total, 1)) * 100));
  return (
    <section className="progress-panel" aria-label="進捗">
      <div className="progress-row">
        <span>
          {current}/{total}
        </span>
        <span>{percent}%</span>
      </div>
      <div className="progress-track">
        <div style={{ width: `${percent}%` }} />
      </div>
    </section>
  );
}
