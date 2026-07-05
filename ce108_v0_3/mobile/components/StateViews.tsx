export function LoadingState({ label = "読み込み中です" }: { label?: string }) {
  return (
    <div className="state-view" role="status">
      <span className="spinner" />
      <p>{label}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state-view error" role="alert">
      <p>{message}</p>
      {onRetry ? (
        <button className="secondary-button" type="button" onClick={onRetry}>
          再試行
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="state-view">
      <p>{message}</p>
    </div>
  );
}
