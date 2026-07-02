import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChoiceCard } from "@/components/ChoiceCard";
import { ConfidenceSelector } from "@/components/ConfidenceSelector";

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
});
