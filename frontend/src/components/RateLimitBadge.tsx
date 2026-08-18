"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getRateLimitStatus,
  RATE_LIMIT_REFRESH_EVENT,
  type RateLimitStatus,
} from "@/lib/api";

function formatCount(n: number): string {
  return n.toLocaleString("en-US");
}

export function RateLimitBadge() {
  const [status, setStatus] = useState<RateLimitStatus | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await getRateLimitStatus();
      setStatus(next);
    } catch {
      // Keep last known value; badge is informational only
    }
  }, []);

  useEffect(() => {
    void refresh();
    const onRefresh = () => void refresh();
    window.addEventListener(RATE_LIMIT_REFRESH_EVENT, onRefresh);
    const id = window.setInterval(() => void refresh(), 60_000);
    return () => {
      window.removeEventListener(RATE_LIMIT_REFRESH_EVENT, onRefresh);
      window.clearInterval(id);
    };
  }, [refresh]);

  if (status?.remaining_requests == null) {
    return (
      <span
        className="hidden text-xs text-stone-400 sm:inline"
        title="Daily request quota unknown until first extraction"
      >
        Rate limit —
      </span>
    );
  }

  const usedLabel =
    status.limit_requests != null
      ? `${formatCount(status.remaining_requests)} / ${formatCount(status.limit_requests)} requests today`
      : `${formatCount(status.remaining_requests)} requests today`;

  const reset = status.reset_requests
    ? ` · resets in ${status.reset_requests}`
    : "";

  return (
    <span
      className="hidden text-xs text-stone-500 sm:inline"
      title={
        status.updated_at
          ? `Daily (RPD) quota · updated ${status.updated_at}`
          : "Daily (RPD) request quota from Groq"
      }
    >
      {usedLabel}
      {reset}
    </span>
  );
}
