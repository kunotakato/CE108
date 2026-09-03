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
      {aid.kind === "acidbase" ? (
        <div className="balance-diagram">
          <div><span>pH</span><strong>酸性/アルカリ性</strong></div>
          <div><span>PaCO2</span><strong>呼吸性</strong></div>
          <div><span>HCO3-</span><strong>代謝性</strong></div>
        </div>
      ) : null}
      {aid.kind === "circulation" ? (
        <div className="circulation-diagram">
          <div>血液量</div>
          <div>ポンプ</div>
          <div>血管抵抗</div>
          <strong>組織灌流</strong>
        </div>
      ) : null}
      {aid.kind === "circuit" ? (
        <div className="circuit-diagram">
          <span>V</span>
          <strong>R</strong>
          <span>I</span>
          <em>V = I R</em>
        </div>
      ) : null}
      {aid.kind === "dialysis" ? (
        <div className="membrane-diagram">
          <div>血液側</div>
          <span>膜</span>
          <div>透析液側</div>
          <strong>拡散 / 限外濾過</strong>
        </div>
      ) : null}
      {aid.kind === "ventilation" ? (
        <div className="lung-diagram">
          <div>FiO2</div>
          <div>VT</div>
          <div>RR</div>
          <div>PEEP</div>
        </div>
      ) : null}
      {aid.kind === "signal" ? (
        <div className="wave-diagram">
          <span />
          <span />
          <span />
          <strong>周波数・波形・雑音</strong>
        </div>
      ) : null}
      <p className="visual-aid-summary">{aid.summary}</p>
    </section>
  );
}
