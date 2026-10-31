import React from "react";
import type { TagStatus } from "@/lib/types";

export type ProvenanceStatus =
  | "suggested"
  | "auto"
  | "verified"
  | "added"
  | "added_by_human"
  | "rejected";

export interface ProvenanceChipProps {
  status: ProvenanceStatus;
  label?: string;
  score?: number;
  interactive?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  className?: string;
}

/**
 * Standard icons per DESIGN.md:
 * - Sparkle for Suggested
 * - Check for Verified
 * - Person for Added
 * - Slash/Cross for Rejected
 */
function SparkleIcon() {
  return (
    <svg
      className="w-3.5 h-3.5 shrink-0"
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M8 0L9.5 6.5L16 8L9.5 9.5L8 16L6.5 9.5L0 8L6.5 6.5L8 0Z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      className="w-3.5 h-3.5 shrink-0"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="3 8.5 6.5 12 13 4" />
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg
      className="w-3.5 h-3.5 shrink-0"
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
    >
      <circle cx="8" cy="5" r="3" />
      <path d="M2.5 14C2.5 11 5 10 8 10C11 10 13.5 11 13.5 14" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" fill="none" />
    </svg>
  );
}

function RejectedIcon() {
  return (
    <svg
      className="w-3.5 h-3.5 shrink-0"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="6" />
      <line x1="4" y1="4" x2="12" y2="12" />
    </svg>
  );
}

/**
 * Normalise raw tag status to one of the 4 core provenance layers
 */
export function normaliseProvenanceStatus(
  status: ProvenanceStatus | TagStatus
): "suggested" | "verified" | "added" | "rejected" {
  switch (status) {
    case "auto":
    case "suggested":
      return "suggested";
    case "verified":
      return "verified";
    case "added_by_human":
    case "added":
      return "added";
    case "rejected":
      return "rejected";
  }
}

export const ProvenanceChip: React.FC<ProvenanceChipProps> = ({
  status,
  label,
  score,
  interactive = false,
  disabled = false,
  onClick,
  className = "",
}) => {
  const norm = normaliseProvenanceStatus(status);

  let styleClasses = "";
  let icon = null;
  let statusText = "";

  switch (norm) {
    case "suggested":
      statusText = "Suggested";
      icon = <SparkleIcon />;
      styleClasses =
        "border-[1.5px] border-dashed border-turmeric bg-transparent text-turmeric hover:bg-turmeric/5";
      break;
    case "verified":
      statusText = "Verified";
      icon = <CheckIcon />;
      styleClasses =
        "border-[1.5px] border-solid border-water bg-water text-paper hover:bg-water/90";
      break;
    case "added":
      statusText = "Added";
      icon = <PersonIcon />;
      styleClasses =
        "border-[1.5px] border-solid border-water bg-transparent text-water hover:bg-water/5";
      break;
    case "rejected":
      statusText = "Rejected";
      icon = <RejectedIcon />;
      styleClasses =
        "border-[1.5px] border-solid border-sandstone/50 bg-stone/40 text-mute line-through";
      break;
  }

  const baseClasses =
    "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-[13px] leading-[18px] font-sans font-medium transition-colors select-none";
  const interactiveClasses = interactive && !disabled
    ? "cursor-pointer focus-ring active:scale-[0.98]"
    : "";
  const disabledClasses = disabled
    ? "opacity-50 cursor-not-allowed pointer-events-none"
    : "";

  const Component = interactive ? "button" : "span";

  return (
    <Component
      type={interactive ? "button" : undefined}
      disabled={interactive ? disabled : undefined}
      onClick={interactive && !disabled ? onClick : undefined}
      className={`${baseClasses} ${styleClasses} ${interactiveClasses} ${disabledClasses} ${className}`}
    >
      {icon}
      {label ? (
        <span className="font-semibold text-ink">
          {label}
          <span className="ml-1.5 font-normal opacity-85">({statusText})</span>
        </span>
      ) : (
        <span>{statusText}</span>
      )}
      {typeof score === "number" && (
        <span
          title="Similarity to the label, not a probability."
          className="ml-1 pl-1.5 border-l border-current/30 text-[11px] tabular-nums font-mono opacity-90"
        >
          {score.toFixed(2)}
        </span>
      )}
    </Component>
  );
};
