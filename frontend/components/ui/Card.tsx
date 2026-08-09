import { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

type CardSize = "sm" | "md" | "lg";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  size?: CardSize;
  raised?: boolean;
}

const radiusClasses: Record<CardSize, string> = {
  sm: "rounded-sm",
  md: "rounded-md",
  lg: "rounded-lg",
};

export function Card({ size = "md", raised = false, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "bg-paper-raised border border-hairline p-6",
        radiusClasses[size],
        raised ? "shadow-raised" : "shadow-card",
        className
      )}
      {...props}
    />
  );
}

export default Card;
