"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  secondary?: ReactNode;
};

export function BottomAction({ children, secondary, ...props }: Props) {
  return (
    <div className="bottom-action">
      {secondary}
      <button className="primary-button" type="button" {...props}>
        {children}
      </button>
    </div>
  );
}
