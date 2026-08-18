import type { ConfidenceStatus } from "@/lib/types";

const STYLES: Record<ConfidenceStatus, string> = {
  high: "bg-emerald-50 text-emerald-800 ring-emerald-200",
  needs_review: "bg-amber-50 text-amber-900 ring-amber-200",
  low: "bg-red-50 text-red-800 ring-red-200",
};

const LABELS: Record<ConfidenceStatus, string> = {
  high: "High confidence",
  needs_review: "Needs review",
  low: "Low confidence",
};

export function ConfidenceBadge({ status }: { status: ConfidenceStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${STYLES[status]}`}
    >
      {LABELS[status]}
    </span>
  );
}
