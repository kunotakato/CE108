"use client";

type Props = {
  code: string;
  text: string;
  selected: boolean;
  onSelect: () => void;
};

export function ChoiceCard({ code, text, selected, onSelect }: Props) {
  return (
    <button className={`choice-card ${selected ? "selected" : ""}`} type="button" onClick={onSelect}>
      <span className="choice-code">{code}</span>
      <span>{text}</span>
    </button>
  );
}
