"use client";

import { InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
}

export function Input({ label, hint, className, ...props }: FieldProps) {
  return (
    <label className="flex flex-col text-body-sm">
      {label && <span className="text-ink mb-1">{label}</span>}
      <input
        className={cn(
          "px-3 py-2 border border-hairline rounded-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-signal focus-visible:border-signal",
          "bg-paper-raised text-ink",
          className
        )}
        {...props}
      />
      {hint && <span className="text-caption text-ink-soft mt-1">{hint}</span>}
    </label>
  );
}

export default Input;
