"use client";

import Link from "next/link";
import { RateLimitBadge } from "./RateLimitBadge";

export function AppHeader() {
  return (
    <header className="border-b border-stone-200 bg-white">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="text-sm font-semibold tracking-tight text-stone-900">
          DocExtract
        </Link>
        <div className="flex items-center gap-5">
          <RateLimitBadge />
          <nav className="flex items-center gap-5 text-sm text-stone-600">
            <Link href="/" className="hover:text-stone-900">
              Upload
            </Link>
            <Link href="/history" className="hover:text-stone-900">
              History
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
