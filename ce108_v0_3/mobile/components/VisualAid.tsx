import type { VisualAid } from "@/lib/types";

export function VisualAidCard({ aid }: { aid?: VisualAid | null }) {
  if (!aid || !aid.steps.length) {
    return null;
  }

  return (
    <section className={`visual-aid visual-aid-${aid.kind}`} aria-label={`${aid.title}の図解`}>
      <div className="visual-aid-header">
        <span className="pill">図解</span>
        <h3>{aid.title}</h3>
      </div>
      <div className="visual-aid-track">
        {aid.steps.map((step, index) => (
          <div className="visual-aid-step-wrap" key={`${step}-${index}`}>
            <div className="visual-aid-step">
              <span>{index + 1}</span>
              <strong>{step}</strong>
            </div>
            {index < aid.steps.length - 1 ? <span className="visual-aid-arrow" aria-hidden="true">→</span> : null}
          </div>
        ))}
      </div>
      <p className="visual-aid-summary">{aid.summary}</p>
    </section>
  );
}
