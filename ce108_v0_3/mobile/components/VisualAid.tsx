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
      {aid.kind === "anatomy" ? (
        <div className="heart-diagram" aria-hidden="true">
          <div className="heart-chamber chamber-ra">右心房<br /><span>洞房結節</span></div>
          <div className="heart-chamber chamber-la">左心房</div>
          <div className="heart-chamber chamber-rv">右心室</div>
          <div className="heart-chamber chamber-lv">左心室</div>
          <div className="conduction-line line-av">房室結節</div>
          <div className="conduction-line line-his">His束</div>
          <div className="conduction-line line-purkinje">Purkinje線維</div>
        </div>
      ) : null}
      {aid.kind === "calculation" && aid.formula ? (
        <div className="formula-diagram">
          <div><span>条件</span><strong>{aid.formula.given}</strong></div>
          <div><span>公式</span><strong>{aid.formula.formula}</strong></div>
          <div><span>代入</span><strong>{aid.formula.substitution}</strong></div>
          <div><span>答え</span><strong>{aid.formula.result}</strong></div>
        </div>
      ) : null}
      <p className="visual-aid-summary">{aid.summary}</p>
    </section>
  );
}
