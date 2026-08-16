import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChoiceCard } from "@/components/ChoiceCard";
import { ConfidenceSelector } from "@/components/ConfidenceSelector";
import { VisualAidCard } from "@/components/VisualAid";

describe("mobile components", () => {
  it("selects a choice with a large tap target", () => {
    const onSelect = vi.fn();
    render(<ChoiceCard code="1" text="選択肢A" selected={false} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: /選択肢A/ }));

    expect(onSelect).toHaveBeenCalledOnce();
  });

  it("changes confidence", () => {
    const onChange = vi.fn();
    render(<ConfidenceSelector value="迷った" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "確実に分かる" }));

    expect(onChange).toHaveBeenCalledWith("確実に分かる");
  });

  it("renders calculation visual aids with formula context", () => {
    render(
      <VisualAidCard
        aid={{
          title: "圧力計算のイメージ",
          kind: "calculation",
          steps: ["条件を確認", "公式を選ぶ", "単位を合わせる", "答えを見る"],
          summary: "式だけでなく、条件から答えまでを順に確認します。",
          formula: {
            given: "F=10 N、A=0.002 m2",
            formula: "P = F / A",
            substitution: "10 / 0.002",
            result: "5,000 Pa",
          },
        }}
      />,
    );

    expect(screen.getByText("圧力計算のイメージ")).toBeInTheDocument();
    expect(screen.getByText("P = F / A")).toBeInTheDocument();
    expect(screen.getByText("5,000 Pa")).toBeInTheDocument();
  });

  it("renders anatomy visual aids with heart landmarks", () => {
    render(
      <VisualAidCard
        aid={{
          title: "刺激伝導の流れ",
          kind: "anatomy",
          steps: ["洞房結節", "房室結節", "His束", "右脚・左脚", "Purkinje線維"],
          summary: "心臓の興奮は上流から下流へ順に伝わります。",
        }}
      />,
    );

    expect(screen.getByText("刺激伝導の流れ")).toBeInTheDocument();
    expect(screen.getByText(/右心房/)).toBeInTheDocument();
    expect(screen.getAllByText("房室結節").length).toBeGreaterThanOrEqual(1);
  });
});
