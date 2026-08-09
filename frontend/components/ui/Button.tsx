"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-ink text-paper hover:bg-signal",
  secondary: "bg-transparent text-ink border border-hairline-strong hover:border-ink",
  ghost: "bg-transparent text-ink-soft hover:text-ink px-1",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center gap-2 rounded-sm px-5 py-3 text-body-sm font-semibold transition-colors duration-150",
          variantClasses[variant],
          className
        )}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";
export default Button;
