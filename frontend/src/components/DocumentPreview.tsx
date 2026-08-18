"use client";

import { useState } from "react";
import { documentFileUrl, documentPreviewUrl } from "@/lib/api";

export function DocumentPreview({
  documentId,
  filename,
}: {
  documentId: string;
  filename: string;
}) {
  // Browser uses same-origin /api/... (Next rewrite → FastAPI)
  const previewSrc = documentPreviewUrl(documentId);
  const fileSrc = documentFileUrl(documentId);
  const [failed, setFailed] = useState(false);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-stone-200 bg-stone-100">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-stone-200 bg-white px-4 py-2">
        <p className="truncate text-sm font-medium text-stone-800">{filename}</p>
        <a
          href={fileSrc}
          target="_blank"
          rel="noreferrer"
          className="shrink-0 text-xs font-medium text-stone-600 underline-offset-2 hover:text-stone-900 hover:underline"
        >
          Open original
        </a>
      </div>

      <div className="relative flex min-h-0 w-full flex-1 items-center justify-center bg-stone-200/60">
        {failed ? (
          <div className="p-6 text-center">
            <p className="text-sm text-stone-600">
              Couldn&apos;t load preview
              <span className="mt-1 block break-all text-xs text-stone-400">
                {previewSrc}
              </span>
            </p>
            <a
              href={fileSrc}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-block text-sm font-medium text-stone-800 underline"
            >
              Open original instead
            </a>
          </div>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewSrc}
            alt={`Preview of ${filename}`}
            className="max-h-full max-w-full object-contain p-4"
            onError={() => setFailed(true)}
          />
        )}
      </div>
    </div>
  );
}
