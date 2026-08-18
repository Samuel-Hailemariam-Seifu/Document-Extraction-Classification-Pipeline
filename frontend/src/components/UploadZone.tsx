"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { uploadDocument } from "@/lib/api";

const ACCEPT = ".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg";
/** Soft client-side pause so rapid re-clicks don't burst past Groq's ~30 RPM. */
const UPLOAD_COOLDOWN_MS = 2500;

export function UploadZone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const cooldownTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const blocked = loading || cooldown;

  useEffect(() => {
    return () => {
      if (cooldownTimer.current) clearTimeout(cooldownTimer.current);
    };
  }, []);

  const startCooldown = useCallback(() => {
    setCooldown(true);
    if (cooldownTimer.current) clearTimeout(cooldownTimer.current);
    cooldownTimer.current = setTimeout(() => {
      setCooldown(false);
      cooldownTimer.current = null;
    }, UPLOAD_COOLDOWN_MS);
  }, []);

  const processFile = useCallback(
    async (file: File) => {
      if (blocked) return;
      setError(null);
      setLoading(true);
      try {
        const doc = await uploadDocument(file);
        startCooldown();
        router.push(`/documents/${doc.id}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
        setLoading(false);
        startCooldown();
      }
    },
    [blocked, router, startCooldown],
  );

  const onFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) void processFile(file);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div className="w-full max-w-xl">
      <div
        role="button"
        tabIndex={blocked ? -1 : 0}
        aria-disabled={blocked}
        onKeyDown={(e) => {
          if (blocked) return;
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onClick={() => !blocked && inputRef.current?.click()}
        onDragEnter={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          setDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!blocked) onFiles(e.dataTransfer.files);
        }}
        className={[
          "relative flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-8 py-16 transition-colors",
          dragging && !blocked
            ? "border-stone-800 bg-stone-100"
            : "border-stone-300 bg-stone-50 hover:border-stone-400 hover:bg-stone-100/80",
          blocked ? "pointer-events-none cursor-not-allowed opacity-70" : "",
        ].join(" ")}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="hidden"
          disabled={blocked}
          onChange={(e) => onFiles(e.target.files)}
        />

        {loading ? (
          <>
            <div className="mb-4 h-8 w-8 animate-spin rounded-full border-2 border-stone-300 border-t-stone-800" />
            <p className="text-sm font-medium text-stone-800">Extracting document…</p>
            <p className="mt-1 text-xs text-stone-500">
              This usually takes a few seconds
            </p>
          </>
        ) : cooldown ? (
          <>
            <p className="text-sm font-medium text-stone-800">Please wait a moment…</p>
            <p className="mt-1 text-xs text-stone-500">
              Brief pause to avoid hitting the per-minute API limit
            </p>
          </>
        ) : (
          <>
            <p className="text-sm font-medium text-stone-900">
              Drop an invoice or receipt here
            </p>
            <p className="mt-1 text-xs text-stone-500">
              PDF, PNG, or JPG — or click to browse
            </p>
          </>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="mt-3 flex items-start justify-between gap-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
        >
          <p className="min-w-0 flex-1">{error}</p>
          <button
            type="button"
            onClick={() => setError(null)}
            className="shrink-0 text-xs font-medium text-red-700 underline-offset-2 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
