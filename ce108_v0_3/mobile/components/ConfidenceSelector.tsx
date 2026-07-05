"use client";

const values = ["確実に分かる", "たぶん分かる", "迷った", "勘で答えた"];

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function ConfidenceSelector({ value, onChange }: Props) {
  return (
    <fieldset className="confidence">
      <legend>自信度</legend>
      <div className="segmented">
        {values.map((item) => (
          <button className={value === item ? "active" : ""} key={item} type="button" onClick={() => onChange(item)}>
            {item}
          </button>
        ))}
      </div>
    </fieldset>
  );
}
